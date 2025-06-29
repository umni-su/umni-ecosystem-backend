import os
import database.database as db
import cv2

from classes.storages.filesystem import Filesystem
from classes.storages.storage import StorageBase
from entities.camera import CameraEntity
from fastapi import Response


class CameraStorage(StorageBase):
    @classmethod
    def upload_cover(cls, camera: CameraEntity, frame: cv2.Mat) -> None | CameraEntity:
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
                camera.cover = rel_path
                sess.add(camera)
                sess.commit()
                sess.refresh(camera)
                return camera

        return None

    @classmethod
    def get_cover(cls, camera: CameraEntity, width: int):
        path = os.path.join(
            camera.storage.path,
            camera.cover
        )
        return cls.image_response(path, width)

    @classmethod
    def camera_path(cls, camera: CameraEntity):
        return os.path.join(
            camera.storage.path,
            str(camera.id)
        )

    @classmethod
    def video_path(cls, camera: CameraEntity):
        return os.path.join(
            cls.camera_path(camera),
            'recordings',
            'stream'
        )

    @classmethod
    def screenshots_path(cls, camera: CameraEntity):
        return os.path.join(
            cls.camera_path(camera),
            'screenshots',
            'stream'
        )

    @classmethod
    def video_detections_path(cls, camera: CameraEntity):
        return os.path.join(
            cls.camera_path(camera),
            'recordings',
            'motions'
        )

    @classmethod
    def screenshots_detections_path(cls, camera: CameraEntity):
        return os.path.join(
            cls.camera_path(camera),
            'screenshots',
            'motions'
        )
