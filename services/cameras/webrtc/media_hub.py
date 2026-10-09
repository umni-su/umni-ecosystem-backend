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
import threading
import time
from fractions import Fraction
from typing import Optional

import av

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType

# RTP-часы видео (90 кГц, как и в aiortc VIDEO_CLOCK_RATE)
VIDEO_CLOCK_RATE = 90000
VIDEO_TIME_BASE = Fraction(1, VIDEO_CLOCK_RATE)

# Аудио для Opus-энкодера aiortc: только 48 кГц s16 stereo/mono
AUDIO_SAMPLE_RATE = 48000
AUDIO_TIME_BASE = Fraction(1, AUDIO_SAMPLE_RATE)


class CameraMediaHub:
    """Раздаёт декодированные кадры одной камеры всем WebRTC-зрителям.

    Кадры приходят из уже существующего потока декодирования CameraStream
    (единственный RTSP-коннект на камеру). Публикация вызывается из потока
    декодирования, а подписчики (треки) ждут кадры в event loop, поэтому
    доставка идёт через ``loop.call_soon_threadsafe``.
    """

    def __init__(
            self,
            camera_id: int,
            max_width: int = 0,
            max_video_queue: int = 4,
            max_audio_queue: int = 32,
    ):
        self.camera_id = camera_id
        self._max_width = max(0, int(max_width or 0))

        self._lock = threading.Lock()
        self._video_subs: set[asyncio.Queue] = set()
        self._audio_subs: set[asyncio.Queue] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self._max_video_queue = max(1, max_video_queue)
        self._max_audio_queue = max(2, max_audio_queue)

        self._clock_start = time.monotonic()
        self._audio_pts = 0
        self._resampler: Optional[av.AudioResampler] = None
        self._target_size: Optional[tuple[int, int]] = None

    # --- Настройки ---------------------------------------------------------

    def set_max_width(self, width: int):
        self._max_width = max(0, int(width or 0))

    def get_target_size(self) -> tuple[int, int]:
        """Размер, к которому приводится видео (для заглушки, пока нет кадров)."""
        with self._lock:
            if self._target_size is not None:
                return self._target_size
        width = self._max_width or 1280
        height = int(round(width * 9 / 16))
        return self._even(width), self._even(height)

    # --- Подписки ----------------------------------------------------------

    def has_video_subscribers(self) -> bool:
        with self._lock:
            return bool(self._video_subs)

    def has_audio_subscribers(self) -> bool:
        with self._lock:
            return bool(self._audio_subs)

    @property
    def has_subscribers(self) -> bool:
        return self.has_video_subscribers() or self.has_audio_subscribers()

    def subscribe_video(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_video_queue)
        with self._lock:
            self._remember_loop_locked()
            self._video_subs.add(queue)
        return queue

    def unsubscribe_video(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._video_subs.discard(queue)

    def subscribe_audio(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_audio_queue)
        with self._lock:
            self._remember_loop_locked()
            self._audio_subs.add(queue)
        return queue

    def unsubscribe_audio(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._audio_subs.discard(queue)

    def _remember_loop_locked(self) -> None:
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None

    # --- Публикация --------------------------------------------------------

    def publish_video(self, frame: av.VideoFrame) -> None:
        """Публикует видео-кадр подписчикам (вызывается из потока декодирования)."""
        with self._lock:
            subs = list(self._video_subs)
            loop = self._loop
        if not subs or loop is None or loop.is_closed():
            return

        try:
            width, height = self._scaled_size(frame.width, frame.height)
            with self._lock:
                self._target_size = (width, height)
            pts = int((time.monotonic() - self._clock_start) * VIDEO_CLOCK_RATE)

            # Каждому зрителю — собственная копия кадра: энкодер aiortc мутирует
            # frame.pict_type, поэтому делить один объект между треками нельзя.
            for queue in subs:
                copy = frame.reformat(width=width, height=height, format='yuv420p')
                copy.pts = pts
                copy.time_base = VIDEO_TIME_BASE
                self._schedule_put(loop, queue, copy)
        except Exception as e:
            Logger.debug(f"[webrtc][camera {self.camera_id}] publish_video failed: {e}", LoggerType.CAMERAS)

    def publish_audio(self, frame: av.AudioFrame) -> None:
        """Публикует аудио-кадр подписчикам (вызывается из потока декодирования)."""
        with self._lock:
            subs = list(self._audio_subs)
            loop = self._loop
        if not subs or loop is None or loop.is_closed():
            return

        try:
            if self._resampler is None:
                self._resampler = av.AudioResampler(
                    format='s16',
                    layout='stereo',
                    rate=AUDIO_SAMPLE_RATE,
                )
            for out in self._resampler.resample(frame):
                out.pts = self._audio_pts
                out.time_base = AUDIO_TIME_BASE
                self._audio_pts += out.samples
                for queue in subs:
                    self._schedule_put(loop, queue, out)
        except Exception as e:
            Logger.debug(f"[webrtc][camera {self.camera_id}] publish_audio failed: {e}", LoggerType.CAMERAS)

    # --- Внутреннее --------------------------------------------------------

    @staticmethod
    def _schedule_put(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, item) -> None:
        try:
            loop.call_soon_threadsafe(CameraMediaHub._put_drop_oldest, queue, item)
        except RuntimeError:
            pass

    @staticmethod
    def _put_drop_oldest(queue: asyncio.Queue, item) -> None:
        try:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(item)
        except Exception:
            pass

    def _scaled_size(self, width: int, height: int) -> tuple[int, int]:
        if self._max_width and width > self._max_width:
            ratio = self._max_width / float(width)
            width = self._max_width
            height = int(round(height * ratio))
        return self._even(width), self._even(height)

    @staticmethod
    def _even(value: int) -> int:
        value = int(value)
        if value < 2:
            return 2
        return value - (value % 2)


class MediaHubRegistry:
    """Глобальный реестр hub'ов камер: camera_id -> CameraMediaHub."""

    _hubs: dict[int, CameraMediaHub] = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, hub: CameraMediaHub) -> None:
        with cls._lock:
            cls._hubs[hub.camera_id] = hub

    @classmethod
    def unregister(cls, camera_id: int) -> None:
        with cls._lock:
            cls._hubs.pop(camera_id, None)

    @classmethod
    def get(cls, camera_id: int) -> Optional[CameraMediaHub]:
        with cls._lock:
            return cls._hubs.get(camera_id)
