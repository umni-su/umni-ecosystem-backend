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

if TYPE_CHECKING:
    from models.camera_model import CameraModelWithRelations
    from services.cameras.classes.camera_stream import CameraStream


class StreamState(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    SHUTTING_DOWN = "shutting_down"
    RESTARTING = "restarting"


class StreamRegistry:
    _streams: List["CameraStream"] = []
    _lock = threading.Lock()
    _state = StreamState.RUNNING
    _restart_callbacks = []

    @classmethod
    def set_state(cls, state: StreamState):
        with cls._lock:
            cls._state = state
            # Уведомляем все зарегистрированные callback'и
            for callback in cls._restart_callbacks:
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
            cls._streams.append(stream)

    @classmethod
    def remove_stream(cls, stream: "CameraStream") -> None:
        with cls._lock:
            if stream in cls._streams:
                cls._streams.remove(stream)

    @classmethod
    def find_by_camera(cls, camera: "CameraModelWithRelations") -> Optional["CameraStream"]:
        with cls._lock:
            for stream in cls._streams:
                if stream.id == camera.id:
                    return stream
            return None

    @classmethod
    def get_all_streams(cls) -> List["CameraStream"]:
        with cls._lock:
            return cls._streams.copy()

    @classmethod
    def stop_all_streams(cls):
        """Останавливает все потоки генерации кадров"""
        with cls._lock:
            for stream in cls._streams:
                try:
                    if hasattr(stream, 'stop_frame_generation'):
                        stream.stop_frame_generation()
                    # Также останавливаем основной поток камеры если нужно
                    if hasattr(stream, 'opened'):
                        stream.opened = False
                except Exception as e:
                    print(f"Error stopping stream {stream.id}: {e}")
