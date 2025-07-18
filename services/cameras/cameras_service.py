import time
from typing import TYPE_CHECKING

from classes.logger import Logger
from classes.thread.Daemon import Daemon

if TYPE_CHECKING:
    from entities.camera import CameraEntity
from repositories.camera_repository import CameraRepository
from services.base_service import BaseService
from services.cameras.classes.camera_stream import CameraStream


class CamerasService(BaseService):
    cameras: list["CameraEntity"]
    streams: list[CameraStream] = []
    checking_thread: Daemon | None = None
    daemon: Daemon | None = None

    @classmethod
    def find_stream_by_camera(cls, camera: "CameraEntity"):
        for stream in CamerasService.streams:
            if stream.id == camera.id:
                return stream
        return None

    def cameras_list_task(self):
        while True:
            self.cameras = CameraRepository.get_cameras()
            for cam in self.cameras:
                current_stream = CamerasService.find_stream_by_camera(camera=cam)
                if isinstance(current_stream, CameraStream):
                    current_stream.set_camera(camera=cam)
                    current_stream.try_capture()
                    # Logger.info(f'[{cam.name}] Update camera in stream list')
                else:
                    CamerasService.streams.append(
                        CameraStream(camera=cam)
                    )
                    # Logger.info(f'[{cam.name}] Add camera to stream list')
            time.sleep(5)

    def run(self):
        Logger.debug('Starting camera streams...')
        self.daemon = Daemon(self.cameras_list_task)
