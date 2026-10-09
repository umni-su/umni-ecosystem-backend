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
from typing import Optional

import av
import cv2
from aiortc import AudioStreamTrack, VideoStreamTrack
from aiortc.mediastreams import AUDIO_PTIME, MediaStreamError

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from services.cameras.utils.cameras_helpers import get_no_signal_frame
from services.cameras.webrtc.media_hub import (
    AUDIO_SAMPLE_RATE,
    AUDIO_TIME_BASE,
    VIDEO_CLOCK_RATE,
    VIDEO_TIME_BASE,
    CameraMediaHub,
)

# Как часто отдавать «нет сигнала», если кадры не приходят (сек)
PLACEHOLDER_INTERVAL = 1.0


class HubVideoTrack(VideoStreamTrack):
    """Видео-трек зрителя, читающий кадры из общего hub'а камеры."""

    kind = "video"

    def __init__(self, hub: CameraMediaHub):
        super().__init__()
        self.hub = hub
        self.queue = hub.subscribe_video()
        self._t0 = time.monotonic()
        self._placeholder_cache: dict[tuple[int, int], av.VideoFrame] = {}

    async def recv(self) -> av.VideoFrame:
        if self.readyState != "live":
            raise MediaStreamError
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=PLACEHOLDER_INTERVAL)
        except asyncio.TimeoutError:
            return self._placeholder()

    def _placeholder(self) -> av.VideoFrame:
        width, height = self.hub.get_target_size()
        frame = self._placeholder_cache.get((width, height))
        if frame is None:
            frame = self._build_placeholder(width, height)
            self._placeholder_cache[(width, height)] = frame
        frame.pts = int((time.monotonic() - self._t0) * VIDEO_CLOCK_RATE)
        frame.time_base = VIDEO_TIME_BASE
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
    """Аудио-трек зрителя. При отсутствии кадров отдаёт тишину."""

    kind = "audio"

    def __init__(self, hub: CameraMediaHub):
        super().__init__()
        self.hub = hub
        self.queue = hub.subscribe_audio()
        self._silence_samples = 0

    async def recv(self) -> av.AudioFrame:
        if self.readyState != "live":
            raise MediaStreamError
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=AUDIO_PTIME)
        except asyncio.TimeoutError:
            return self._silence()

    def _silence(self) -> av.AudioFrame:
        samples = int(AUDIO_PTIME * AUDIO_SAMPLE_RATE)
        frame = av.AudioFrame(format='s16', layout='stereo', samples=samples)
        for plane in frame.planes:
            plane.update(bytes(plane.buffer_size))
        frame.sample_rate = AUDIO_SAMPLE_RATE
        frame.pts = self._silence_samples
        frame.time_base = AUDIO_TIME_BASE
        self._silence_samples += samples
        return frame

    async def close(self) -> None:
        try:
            self.hub.unsubscribe_audio(self.queue)
        except Exception:
            pass
        self.stop()
