import classes.crypto.crypto as crypto
from classes.logger import Logger
from entities.camera import CameraEntity
from entities.enums.camera_protocol_enum import CameraProtocolEnum
from models.camera_model import CameraBaseModel
from repositories.base_repository import BaseRepository
from sqlmodel import select

from repositories.storage_repository import StorageRepository


class CameraRepository(BaseRepository):
    @classmethod
    def get_cameras(cls):
        with cls.query() as sess:
            cameras = sess.exec(
                select(CameraEntity)
            ).all()
            return cameras

    @classmethod
    def get_camera(cls, camera_id: int) -> CameraEntity | None:
        with cls.query() as sess:
            return sess.exec(
                select(CameraEntity).where(CameraEntity.id == camera_id)
            ).first()

    @classmethod
    def add_camera(cls, model: CameraBaseModel):
        camera = cls.prepare_camera(model, CameraEntity())
        with cls.query() as sess:
            sess.add(camera)
            sess.commit()
            sess.refresh(camera)
            return camera

    @classmethod
    def update_camera(cls, model: CameraBaseModel):
        with cls.query() as sess:
            cam = cls.get_camera(model.id)
            camera = cls.prepare_camera(model, cam)
            sess.add(camera)
            sess.commit()
            sess.refresh(camera)
            return camera

    @classmethod
    def prepare_camera(cls, model: CameraBaseModel, target: CameraEntity):
        camera = target
        try:
            storage = StorageRepository.get_storage(model.storage_id)
            if camera.storage != storage:
                camera.storage = storage
            camera.name = model.name
            camera.active = model.active
            camera.alerts = model.active
            camera.record = model.record
            camera.record_mode = model.record_mode
            camera.record_duration = model.record_duration
            camera.delete_after = model.delete_after
            camera.username = model.username
            if model.protocol is not CameraProtocolEnum.USB:
                camera.ip = model.ip
                camera.port = model.port
            camera.protocol = model.protocol
            if model.password is not None:
                camera.password = crypto.Crypto.encrypt(model.password)
            else:
                model.password = None
            camera.primary = model.primary
            camera.secondary = model.secondary
            return camera

        except Exception as e:
            Logger.err(e)
