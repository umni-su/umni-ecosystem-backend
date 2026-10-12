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
"""CPU-оптимизация WebRTC-энкодера.

aiortc создаёт libx264 без параметра ``preset`` (по умолчанию ffmpeg берёт
``medium``), что тяжело для слабых CPU (LXC с 1–2 ядрами). Здесь мы
подменяем энкодер на libx264 с ``preset=ultrafast`` — при ``tune=zerolatency``
это в разы дешевле при том же профиле Baseline.

Реализация повторяет ``aiortc.codecs.h264.H264Encoder._encode_frame`` из
aiortc==1.15.0 (версия закреплена в requirements.txt) с единственным
изменением — добавлен ``preset``.
"""

import fractions
from collections.abc import Iterator

import av
from aiortc.codecs.h264 import H264Encoder, MAX_FRAME_RATE

import aiortc.codecs as _codecs
import aiortc.rtcrtpsender as _rtcrtpsender


class RealtimeH264Encoder(H264Encoder):
    """H264-энкодер libx264 в режиме, пригодном для realtime на слабом CPU."""

    def _encode_frame(
        self, frame: av.VideoFrame, force_keyframe: bool
    ) -> Iterator[bytes]:
        if self.codec and (
            frame.width != self.codec.width
            or frame.height != self.codec.height
            # we only adjust bitrate if it changes by over 10%
            or abs(self.target_bitrate - self.codec.bit_rate) / self.codec.bit_rate
            > 0.1
        ):
            self.buffer_data = b""
            self.buffer_pts = None
            self.codec = None

        if force_keyframe:
            # force a complete image
            frame.pict_type = av.video.frame.PictureType.I
        else:
            # reset the picture type, otherwise no B-frames are produced
            frame.pict_type = av.video.frame.PictureType.NONE

        if self.codec is None:
            self.codec = av.CodecContext.create("libx264", "w")
            self.codec.width = frame.width
            self.codec.height = frame.height
            self.codec.bit_rate = self.target_bitrate
            self.codec.pix_fmt = "yuv420p"
            self.codec.framerate = fractions.Fraction(MAX_FRAME_RATE, 1)
            self.codec.time_base = fractions.Fraction(1, MAX_FRAME_RATE)
            self.codec.options = {
                "level": "31",
                "tune": "zerolatency",
                "preset": "ultrafast",
            }
            self.codec.profile = "Baseline"

        data_to_send = b""
        for package in self.codec.encode(frame):
            data_to_send += bytes(package)

        if data_to_send:
            yield from self._split_bitstream(data_to_send)


_patched = False


def apply_realtime_encoder() -> None:
    """Подменяет фабрику энкодеров aiortc на нашу (идемпотентно)."""
    global _patched
    if _patched:
        return

    _original_get_encoder = _codecs.get_encoder

    def _get_encoder(codec):
        if codec.mimeType.lower() == "video/h264":
            return RealtimeH264Encoder()
        return _original_get_encoder(codec)

    # rtcrtpsender импортирует get_encoder напрямую в свой namespace
    _codecs.get_encoder = _get_encoder
    _rtcrtpsender.get_encoder = _get_encoder
    _patched = True
