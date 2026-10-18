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

from typing import List, Optional, TYPE_CHECKING
import threading
import time
from enum import Enum

from models.camera_stream_model import CameraStreamModel

if TYPE_CHECKING:
    from models.camera_model import CameraModelWithRelations
    from services.cameras.classes.camera_stream import CameraStream


class StreamState(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    SHUTTING_DOWN = "shutting_down"
    RESTARTING = "restarting"


class StreamRegistry:
    # Индекс потоков по id камеры: O(1) поиск вместо линейного скана
    _streams: dict[int, "CameraStream"] = {}
    _lock = threading.Lock()
    _state = StreamState.RUNNING
    _restart_callbacks = []

    @classmethod
    def set_state(cls, state: StreamState):
        with cls._lock:
            cls._state = state
            # Снимаем копию callback'ов под блокировкой...
            callbacks = list(cls._restart_callbacks)
        # ...а вызываем вне неё, чтобы не держать lock во время работы
        # callback'ов (join потоков, рестарты) и не провоцировать дедлоки
        for callback in callbacks:
            try:
                callback(state)
            except Exception as e:
                print(f"Error in restart callback: {e}")

    @classmethod
    def get_state(cls) -> StreamState:
        with cls._lock:
            return cls._state

    @classmethod
    def register_restart_callback(cls, callback):
        with cls._lock:
            cls._restart_callbacks.append(callback)

    @classmethod
    def is_shutting_down(cls):
        return cls.get_state() == StreamState.SHUTTING_DOWN

    @classmethod
    def is_restarting(cls):
        return cls.get_state() == StreamState.RESTARTING

    @classmethod
    def is_running(cls):
        return cls.get_state() == StreamState.RUNNING

    @classmethod
    def add_stream(cls, stream: "CameraStream") -> None:
        with cls._lock:
            cls._streams[stream.id] = stream

    @classmethod
    def remove_stream(cls, stream: "CameraStream") -> None:
        with cls._lock:
            cls._streams.pop(stream.id, None)

    @classmethod
    def find_by_camera(cls, camera: "CameraModelWithRelations") -> Optional["CameraStream"]:
        with cls._lock:
            return cls._streams.get(camera.id)

    @classmethod
    def get_all_streams(cls) -> List["CameraStream"]:
        with cls._lock:
            return list(cls._streams.values())

    @classmethod
    def stop_all_streams(cls):
        """Останавливает все потоки камер"""
        # Работаем по снимку вне блокировки: остановка потоков может блокировать
        streams = cls.get_all_streams()
        for stream in streams:
            try:
                if hasattr(stream, 'opened'):
                    stream.opened = False
            except Exception as e:
                print(f"Error stopping stream {stream.id}: {e}")

    @classmethod
    def get_streams_as_models(cls):
        res = []
        streams = StreamRegistry.get_all_streams()
        # Один снимок времени на весь список: значения в ответе должны быть
        # согласованы между собой, а не посчитаны в разные моменты.
        now = time.time()
        for stream in streams:
            last_frame_time = stream.last_frame_time
            has_live_frame = (
                0 < last_frame_time
                and now - last_frame_time <= stream.heartbeat_timeout
            )
            res.append(
                CameraStreamModel(
                    name=stream.camera.name,
                    camera_id=stream.id,
                    stopped=stream.is_stopped(),
                    need_restart=stream.need_restart,
                    capture_error=stream.capture_error,
                    running=stream.opened and not stream.is_stopped(),
                    recording=bool(stream.write),
                    has_live_frame=has_live_frame,
                    last_frame_age_sec=(
                        round(now - last_frame_time, 2)
                        if last_frame_time else None
                    ),
                    need_skip=stream.need_skip,
                )
            )
        return res
