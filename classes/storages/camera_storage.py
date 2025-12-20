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

import cv2
import os
from datetime import datetime
from typing import TYPE_CHECKING
from numpy import ndarray
from pydantic import BaseModel
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.storages.filesystem import Filesystem
from classes.storages.storage import StorageBase
from database.session import write_session
from entities.camera import CameraEntity
from services.cameras.utils.cameras_helpers import get_no_signal_frame

if TYPE_CHECKING:
    from models.camera_model import CameraModelWithRelations


class ScreenshotResultModel(BaseModel):
    success: bool = False
    directory: str
    filename: str
    full_path: str


class CameraStorage(StorageBase):
    @classmethod
    def upload_cover(cls, camera: "CameraModelWithRelations", frame: cv2.Mat):

        try:
            cls.path = camera.storage.path
            rel_path = os.path.join(
                str(camera.id),
                f'cover_{cls.date_filename()}.jpg'
            )
            image_path = os.path.join(
                cls.path,
                rel_path
            )
            if not cls.exists(os.path.dirname(image_path)):
                Filesystem.mkdir(os.path.dirname(image_path))
            if cv2.imwrite(image_path, frame):

                cls.remove_cover_file(camera)

                with write_session() as session:
                    try:
                        cam = session.get(CameraEntity, camera.id)
                        cam.cover = rel_path
                        session.add(cam)
                        Logger.debug(f"[{camera.name}] upload_cover to {image_path}")
                    except Exception as e:
                        Logger.err(f"[{camera.name}]  error upload_cover to {image_path} code: {str(e)}")
                return camera
        except Exception as e:
            Logger.err(f"[{camera.name}] upload_cover error - {e}", LoggerType.STORAGES)
            raise e

    @classmethod
    def remove_cover_file(cls, camera: "CameraModelWithRelations") -> bool:
        prev_path = camera.cover
        if camera.cover is not None:
            full_path = os.path.join(
                cls.path,
                prev_path
            )
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                    return True
                except Exception as e:
                    Logger.err(str(e), LoggerType.CAMERAS)
                    return False
        return False

    @classmethod
    def date_filename(cls):
        return datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')

    @classmethod
    def take_detection_screenshot(cls, camera: "CameraModelWithRelations", frame: cv2.Mat | ndarray | None = None,
                                  prefix: str = None):
        path = cls.screenshots_detections_path(camera)
        return cls._save_camera_image(path, frame, prefix)

    @classmethod
    def take_screenshot(cls, camera: "CameraModelWithRelations", frame: cv2.Mat | ndarray | None = None,
                        prefix: str = None):
        path = cls.screenshots_path(camera)
        return cls._save_camera_image(path, frame, prefix)

    @classmethod
    def _save_camera_image(cls, path: str, frame: cv2.Mat | ndarray | None = None, prefix: str = None):

        if prefix:
            filename = '.'.join([prefix, cls.date_filename(), 'jpg'])
        else:
            filename = '.'.join([cls.date_filename(), 'jpg'])
        if not Filesystem.exists(path):
            Filesystem.mkdir(path_or_filename=path, recursive=True)
        _dir = path
        path = os.path.join(
            _dir,
            filename
        )
        res = cv2.imwrite(
            filename=path,
            img=frame
        )
        return ScreenshotResultModel(
            success=res,
            directory=_dir,
            filename=filename,
            full_path=os.path.join(_dir, filename)
        )

    @classmethod
    def get_cover(cls, camera: "CameraModelWithRelations", width: int):
        path = os.path.join(
            camera.storage.path,
            camera.cover
        )
        if os.path.exists(path):
            return cls.image_response(path, width)
        else:
            return get_no_signal_frame(width=width)

    @classmethod
    def camera_path(cls, camera: "CameraModelWithRelations"):
        return os.path.join(
            camera.storage.path,
            str(camera.id)
        )

    @classmethod
    def video_path(cls, camera: "CameraModelWithRelations"):
        return os.path.join(
            cls.camera_path(camera),
            'recordings',
            'stream'
        )

    @classmethod
    def screenshots_path(cls, camera: "CameraModelWithRelations"):
        return os.path.join(
            cls.camera_path(camera),
            'screenshots',
            'stream'
        )

    @classmethod
    def video_detections_path(cls, camera: "CameraModelWithRelations"):
        return os.path.join(
            cls.camera_path(camera),
            'recordings',
            'motions'
        )

    @classmethod
    def screenshots_detections_path(cls, camera: "CameraModelWithRelations"):
        return os.path.join(
            cls.camera_path(camera),
            'screenshots',
            'motions'
        )
