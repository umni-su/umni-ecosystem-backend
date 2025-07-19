import os
from datetime import datetime
from typing import TYPE_CHECKING

from numpy import ndarray
from pydantic import BaseModel

import database.database as db
import cv2

from classes.logger import Logger
from classes.storages.filesystem import Filesystem
from classes.storages.storage import StorageBase

if TYPE_CHECKING:
    from entities.camera import CameraEntity


class ScreenshotResultModel(BaseModel):
    success: bool = False
    directory: str
    filename: str


class CameraStorage(StorageBase):
    @classmethod
    def upload_cover(cls, camera: "CameraEntity", frame: cv2.Mat):
        cls.path = camera.storage.path
        rel_path = os.path.join(
            str(camera.id),
            'cover.jpg'
        )
        image_path = os.path.join(
            cls.path,
            rel_path
        )
        if not cls.exists(os.path.dirname(image_path)):
            Filesystem.mkdir(os.path.dirname(image_path))
        if cv2.imwrite(image_path, frame):
            with db.get_separate_session() as sess:
                try:
                    camera.cover = rel_path
                    sess.add(camera)
                    sess.commit()
                    sess.refresh(camera)
                    return camera
                except Exception as e:
                    Logger.err(e)

        return None

    @classmethod
    def date_filename(self):
        return datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')

    @classmethod
    def take_detection_screenshot(cls, camera: "CameraEntity", frame: cv2.Mat | ndarray | None = None,
                                  prefix: str = None):
        path = cls.screenshots_detections_path(camera)
        return cls._save_camera_image(path, frame, prefix)

    @classmethod
    def take_screenshot(cls, camera: "CameraEntity", frame: cv2.Mat | ndarray | None = None, prefix: str = None):
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
        path = os.path.join(
            path,
            filename
        )
        res = cv2.imwrite(
            filename=path,
            img=frame
        )
        return ScreenshotResultModel(
            success=res,
            directory=path,
            filename=filename,
        )

    @classmethod
    def get_cover(cls, camera: "CameraEntity", width: int):
        path = os.path.join(
            camera.storage.path,
            camera.cover
        )
        return cls.image_response(path, width)

    @classmethod
    def camera_path(cls, camera: "CameraEntity"):
        return os.path.join(
            camera.storage.path,
            str(camera.id)
        )

    @classmethod
    def video_path(cls, camera: "CameraEntity"):
        return os.path.join(
            cls.camera_path(camera),
            'recordings',
            'stream'
        )

    @classmethod
    def screenshots_path(cls, camera: "CameraEntity"):
        return os.path.join(
            cls.camera_path(camera),
            'screenshots',
            'stream'
        )

    @classmethod
    def video_detections_path(cls, camera: "CameraEntity"):
        return os.path.join(
            cls.camera_path(camera),
            'recordings',
            'motions'
        )

    @classmethod
    def screenshots_detections_path(cls, camera: "CameraEntity"):
        return os.path.join(
            cls.camera_path(camera),
            'screenshots',
            'motions'
        )
