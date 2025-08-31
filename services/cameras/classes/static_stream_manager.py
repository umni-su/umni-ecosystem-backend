# Copyright (C) 2025 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Менеджер для статичных заставок
import cv2
import asyncio
import threading

from classes.app.lifespan_manager import lifespan_manager
from repositories.camera_repository import CameraRepository
from services.cameras.classes.stream_registry import StreamRegistry
from services.cameras.utils.cameras_helpers import get_no_signal_frame


class StaticStreamManager:
    _instance = None
    _lock = threading.Lock()
    _active_streams: dict[int, bool] = {}

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def generate_static_placeholder(self, camera_id: int, camera_name: str):
        """Генерирует статичную заставку с периодической проверкой доступности потока"""
        check_interval = 3
        max_retries = 100

        retry_count = 0
        self._active_streams[camera_id] = True

        try:
            while (self._active_streams.get(camera_id, False) and
                   retry_count < max_retries and
                   not lifespan_manager.is_shutting_down):

                # Проверяем, доступен ли поток
                camera = CameraRepository.get_camera(camera_id)
                stream = StreamRegistry.find_by_camera(camera)

                if stream and stream.opened and StreamRegistry.is_running():
                    break

                # Генерируем заставку
                placeholder = get_no_signal_frame(width=640)
                ret, buffer = cv2.imencode('.jpg', placeholder)

                if ret:
                    frame_data = (b'--frame\r\n'
                                  b'Content-Type: image/jpeg\r\n\r\n' +
                                  buffer.tobytes() + b'\r\n')
                    yield frame_data

                retry_count += 1
                await asyncio.sleep(check_interval)

        finally:
            self._active_streams.pop(camera_id, None)


static_stream_manager = StaticStreamManager.get_instance()
