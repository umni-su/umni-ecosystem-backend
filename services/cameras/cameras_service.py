import time
from typing import TYPE_CHECKING

from classes.logger import Logger
from classes.thread.Daemon import Daemon
from services.cameras.classes.stream_registry import StreamRegistry
from services.cameras.utils.stream_utils import find_stream_by_camera

if TYPE_CHECKING:
    from entities.camera import CameraEntity
from repositories.camera_repository import CameraRepository
from services.base_service import BaseService
from services.cameras.classes.camera_stream import CameraStream


class CamerasService(BaseService):
    name = "cameras"
    cameras: list["CameraEntity"]
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
                    Logger.info(f'[{cam.name}] Обновлена камера в списке потоков')
                else:
                    new_stream = CameraStream(camera=cam)
                    StreamRegistry.add_stream(new_stream)  # Добавляем поток в реестр
                    Logger.info(f'[{cam.name}] Добавлен новый поток')
            time.sleep(5)

    def run(self):
        Logger.debug('Starting camera streams...')
        self.daemon = Daemon(self.cameras_list_task)
