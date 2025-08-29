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

import time
from typing import TYPE_CHECKING

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.thread.daemon import Daemon
from services.cameras.classes.stream_registry import StreamRegistry

from repositories.camera_repository import CameraRepository
from services.base_service import BaseService
from services.cameras.classes.camera_stream import CameraStream

if TYPE_CHECKING:
    from models.camera_model import CameraModelWithRelations


class CamerasService(BaseService):
    name = "cameras"
    cameras: list["CameraModelWithRelations"]
    streams: list[CameraStream] = []
    checking_thread: Daemon | None = None
    daemon: Daemon | None = None

    def cameras_list_task(self):
        while True:
            self.cameras = CameraRepository.get_cameras()
            for cam in self.cameras:
                current_stream = StreamRegistry.find_by_camera(cam)  # Используем StreamRegistry
                if current_stream:
                    current_stream.set_camera(cam)
                    Logger.debug(f'[{cam.name}] Update camera in camera registry', LoggerType.CAMERAS)
                else:
                    new_stream = CameraStream(camera=cam)
                    StreamRegistry.add_stream(new_stream)  # Добавляем поток в реестр
                    Logger.debug(f'[{cam.name}] New stream added', LoggerType.CAMERAS)
            time.sleep(5)

    def run(self):
        Logger.debug('Starting camera streams...', LoggerType.CAMERAS)
        self.daemon = Daemon(self.cameras_list_task)
