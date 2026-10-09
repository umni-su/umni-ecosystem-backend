#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import time
from fractions import Fraction

import av
import cv2
from aiortc import AudioStreamTrack, VideoStreamTrack
from aiortc.mediastreams import (
    AUDIO_PTIME,
    VIDEO_CLOCK_RATE,
    VIDEO_PTIME,
    VIDEO_TIME_BASE,
    MediaStreamError,
)

from services.cameras.utils.cameras_helpers import get_no_signal_frame
from services.cameras.webrtc.media_hub import (
    AUDIO_SAMPLE_RATE,
    AUDIO_TIME_BASE,
    CameraMediaHub,
)

# Аудио, которое ожидает Opus-энкодер aiortc.
AUDIO_SAMPLES_PER_FRAME = 960          # 20 мс при 48 кГц
AUDIO_CHANNELS = 2
AUDIO_SAMPLE_WIDTH = 2                 # s16
AUDIO_FRAME_BYTES = AUDIO_SAMPLES_PER_FRAME * AUDIO_CHANNELS * AUDIO_SAMPLE_WIDTH

# Предел внутреннего аудио-буфера (~1 с), чтобы декодер с read-ahead не рос бесконечно.
AUDIO_BUFFER_MAX_BYTES = AUDIO_SAMPLE_RATE * AUDIO_CHANNELS * AUDIO_SAMPLE_WIDTH

# Сколько накопить перед стартом выдачи (jitter-буфер ~80 мс) и сколько ждать при голоде.
AUDIO_PREFILL_FRAMES = 4
AUDIO_STARVE_GRACE = 0.02


class HubVideoTrack(VideoStreamTrack):
    """Видео-трек зрителя, читающий кадры из общего hub'а камеры.

    Кадры отдаются с пейсингом по стенным часам (30 fps) — независимо от того,
    как декодер публикует кадры пачками. Всегда берём самый свежий кадр и
    выбрасываем устаревшие: это держит низкую задержку и плавную картинку.
    """

    kind = "video"

    def __init__(self, hub: CameraMediaHub):
        super().__init__()
        self.hub = hub
        self.queue = hub.subscribe_video()
        self._start: float | None = None
        self._timestamp = 0
        self._placeholder_cache: dict[tuple[int, int], av.VideoFrame] = {}

    async def recv(self) -> av.VideoFrame:
        if self.readyState != "live":
            raise MediaStreamError

        pts, time_base = await self._next_timestamp()

        frame = await self._pop_latest()
        if frame is None:
            frame = self._placeholder()

        frame.pts = pts
        frame.time_base = time_base
        return frame

    async def _next_timestamp(self) -> tuple[int, Fraction]:
        if self._start is None:
            self._start = time.time()
        else:
            self._timestamp += int(VIDEO_PTIME * VIDEO_CLOCK_RATE)
            wait = self._start + (self._timestamp / VIDEO_CLOCK_RATE) - time.time()
            if wait > 0:
                await asyncio.sleep(wait)
        return self._timestamp, VIDEO_TIME_BASE

    async def _pop_latest(self) -> av.VideoFrame | None:
        """Возвращает самый свежий кадр, опустошая очередь (drop stale)."""
        frame = None
        while True:
            try:
                frame = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        if frame is None:
            # На тик пейсинга кадра может ещё не быть — коротко подождём.
            try:
                frame = await asyncio.wait_for(self.queue.get(), timeout=float(VIDEO_PTIME))
            except asyncio.TimeoutError:
                return None
            # Возможно, за время ожидания пришли более свежие кадры.
            while True:
                try:
                    frame = self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        return frame

    def _placeholder(self) -> av.VideoFrame:
        width, height = self.hub.get_target_size()
        frame = self._placeholder_cache.get((width, height))
        if frame is None:
            frame = self._build_placeholder(width, height)
            self._placeholder_cache[(width, height)] = frame
        return frame

    @staticmethod
    def _build_placeholder(width: int, height: int) -> av.VideoFrame:
        try:
            image = get_no_signal_frame(width=width)
            if image is None or getattr(image, 'size', 0) == 0:
                image = None
        except Exception:
            image = None
        if image is None:
            image = av.VideoFrame(width=width, height=height)
            return image.reformat(format='yuv420p')
        image = cv2.resize(image, (width, height))
        return av.VideoFrame.from_ndarray(image, format='bgr24').reformat(format='yuv420p')

    async def close(self) -> None:
        try:
            self.hub.unsubscribe_video(self.queue)
        except Exception:
            pass
        self.stop()


class HubAudioTrack(AudioStreamTrack):
    """Аудио-трек зрителя.

    Приводит разрозненные кадры из hub'а к ровному потоку кадров по 20 мс
    (960 сэмплов, s16 stereo 48 кГц) с пейсингом по стенным часам и монотонным
    pts. Тишина добивается только при реальном голоде — как jitter-буфер.
    """

    kind = "audio"

    def __init__(self, hub: CameraMediaHub):
        super().__init__()
        self.hub = hub
        self.queue = hub.subscribe_audio()
        self._pcm = bytearray()
        self._start: float | None = None
        self._timestamp = 0            # исходящий pts (сэмплы)
        self._prefilled = False

    async def recv(self) -> av.AudioFrame:
        if self.readyState != "live":
            raise MediaStreamError

        await self._pace()

        if not self._prefilled:
            await self._prefill()

        self._drain_queue()
        if len(self._pcm) < AUDIO_FRAME_BYTES:
            await self._grace_fill()

        chunk = self._take(AUDIO_FRAME_BYTES)

        frame = av.AudioFrame(format='s16', layout='stereo', samples=AUDIO_SAMPLES_PER_FRAME)
        frame.planes[0].update(chunk)
        frame.sample_rate = AUDIO_SAMPLE_RATE
        frame.pts = self._timestamp
        frame.time_base = AUDIO_TIME_BASE
        return frame

    async def _pace(self) -> None:
        if self._start is None:
            self._start = time.time()
            return
        self._timestamp += AUDIO_SAMPLES_PER_FRAME
        wait = self._start + (self._timestamp / AUDIO_SAMPLE_RATE) - time.time()
        if wait > 0:
            await asyncio.sleep(wait)

    async def _prefill(self) -> None:
        """Накапливает небольшой буфер, чтобы старт был без провалов."""
        deadline = time.time() + 0.25
        self._drain_queue()
        while len(self._pcm) < AUDIO_PREFILL_FRAMES * AUDIO_FRAME_BYTES and time.time() < deadline:
            try:
                frame = await asyncio.wait_for(self.queue.get(), timeout=AUDIO_PTIME)
            except asyncio.TimeoutError:
                break
            self._append(frame)
        self._prefilled = True

    async def _grace_fill(self) -> None:
        """Короткое ожидание при нехватке данных, чтобы избежать лишней тишины."""
        try:
            frame = await asyncio.wait_for(self.queue.get(), timeout=AUDIO_STARVE_GRACE)
        except asyncio.TimeoutError:
            return
        self._append(frame)
        self._drain_queue()

    def _drain_queue(self) -> None:
        while True:
            try:
                frame = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            self._append(frame)

    def _append(self, frame: av.AudioFrame) -> None:
        data = bytes(frame.planes[0]) if len(frame.planes) == 1 else b''.join(bytes(p) for p in frame.planes)
        self._pcm.extend(data)
        if len(self._pcm) > AUDIO_BUFFER_MAX_BYTES:
            del self._pcm[:len(self._pcm) - AUDIO_BUFFER_MAX_BYTES]

    def _take(self, size: int) -> bytes:
        if len(self._pcm) >= size:
            chunk = bytes(self._pcm[:size])
            del self._pcm[:size]
            return chunk
        # Не хватает данных — добиваем тишиной.
        chunk = bytes(self._pcm) + bytes(size - len(self._pcm))
        self._pcm.clear()
        return chunk

    async def close(self) -> None:
        try:
            self.hub.unsubscribe_audio(self.queue)
        except Exception:
            pass
        self.stop()
