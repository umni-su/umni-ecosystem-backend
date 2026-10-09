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

import av
from aiortc import AudioStreamTrack, VideoStreamTrack
from aiortc.mediastreams import AUDIO_PTIME, MediaStreamError

from services.cameras.webrtc.media_hub import (
    AUDIO_SAMPLE_RATE,
    AUDIO_TIME_BASE,
    CameraMediaHub,
)

# Кадр Opus: 20 мс при 48 кГц, s16 stereo.
AUDIO_SAMPLES_PER_FRAME = int(AUDIO_PTIME * AUDIO_SAMPLE_RATE)  # 960
AUDIO_FRAME_BYTES = AUDIO_SAMPLES_PER_FRAME * 2 * 2
# Предел внутреннего буфера (~1 с), чтобы не расти бесконечно при отставании.
AUDIO_BUFFER_MAX_BYTES = AUDIO_SAMPLE_RATE * 2 * 2


class HubVideoTrack(VideoStreamTrack):
    """Видео-трек зрителя, читающий кадры из общего hub'а камеры.

    У каждого зрителя своя целевая ширина (``max_width``): кадр из hub'а
    масштабируется под неё в ``recv``. Всегда создаём свежий объект кадра —
    aiortc-энкодер мутирует отданный кадр (``pict_type``), а источник в hub'е
    общий для всех зрителей.
    """

    kind = "video"

    def __init__(self, hub: CameraMediaHub, max_width: int | None = None):
        super().__init__()
        self.hub = hub
        self.queue = hub.subscribe_video()
        self._max_width = max(0, int(max_width or 0))

    def set_max_width(self, width: int) -> None:
        """Меняет целевое разрешение на лету (применяется на следующем кадре)."""
        self._max_width = max(0, int(width or 0))

    async def recv(self) -> av.VideoFrame:
        if self.readyState != "live":
            raise MediaStreamError
        frame = await self.queue.get()

        pts = frame.pts
        time_base = frame.time_base
        width = self._target_width(frame.width)
        height = self._target_height(frame, width)

        # Всегда создаём новый объект, даже если размеры совпали
        frame = frame.reformat(width=width, height=height, format='yuv420p')
        frame.pts = pts
        frame.time_base = time_base
        return frame

    @staticmethod
    def _copy_frame(frame: av.VideoFrame) -> av.VideoFrame:
        copy = av.VideoFrame(width=frame.width, height=frame.height, format=frame.format.name)
        for index, plane in enumerate(frame.planes):
            copy.planes[index].update(bytes(plane))
        return copy

    def _target_width(self, src_width: int) -> int:
        if self._max_width and src_width > self._max_width:
            return self._max_width
        return src_width

    @staticmethod
    def _target_height(frame: av.VideoFrame, width: int) -> int:
        height = round(width * frame.height / frame.width) if frame.width else 0
        if height < 2:
            height = 2
        return height - (height % 2)

    async def close(self) -> None:
        try:
            self.hub.unsubscribe_video(self.queue)
        except Exception:
            pass
        self.stop()


class HubAudioTrack(AudioStreamTrack):
    """Аудио-трек зрителя.

    Кадры декодера приходят неровно (пачками), а Opus-сендер aiortc для
    аудио не спит сам — поэтому пейсим recv по стенным часам (20 мс) и выдаём
    ровно по 960 сэмплов 48 кГц s16 stereo. Недобор добиваем тишиной.
    """

    kind = "audio"

    def __init__(self, hub: CameraMediaHub):
        super().__init__()
        self.hub = hub
        self.queue = hub.subscribe_audio()
        self._pcm = bytearray()
        self._start: float | None = None
        self._timestamp = 0

    async def recv(self) -> av.AudioFrame:
        if self.readyState != "live":
            raise MediaStreamError

        await self._pace()
        self._drain()
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
        wait = self._start + self._timestamp / AUDIO_SAMPLE_RATE - time.time()
        if wait > 0:
            await asyncio.sleep(wait)

    def _drain(self) -> None:
        while True:
            try:
                frame = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            self._pcm.extend(bytes(frame.planes[0]))
        if len(self._pcm) > AUDIO_BUFFER_MAX_BYTES:
            del self._pcm[:len(self._pcm) - AUDIO_BUFFER_MAX_BYTES]

    def _take(self, size: int) -> bytes:
        if len(self._pcm) >= size:
            chunk = bytes(self._pcm[:size])
            del self._pcm[:size]
            return chunk
        chunk = bytes(self._pcm) + bytes(size - len(self._pcm))
        self._pcm.clear()
        return chunk

    async def close(self) -> None:
        try:
            self.hub.unsubscribe_audio(self.queue)
        except Exception:
            pass
        self.stop()
