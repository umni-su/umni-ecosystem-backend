from config.dependencies import get_ecosystem
from classes.logger import Logger
from database.session import write_session
from entities.camera import CameraEntity
from entities.enums.camera_protocol_enum import CameraProtocolEnum
from models.camera_model import CameraBaseModel, CameraModelWithRelations
from repositories.base_repository import BaseRepository
from sqlmodel import select

from repositories.storage_repository import StorageRepository


class CameraRepository(BaseRepository):
    @classmethod
    def get_cameras(cls):
        with write_session() as sess:
            try:
                cameras = sess.exec(
                    select(CameraEntity)
                ).all()

                return [
                    CameraModelWithRelations.model_validate(
                        camera.to_dict(
                            include_relationships=True
                        )
                    )
                    for camera in cameras
                ]
            except Exception as e:
                Logger.err(str(e))

    @classmethod
    def get_camera(cls, camera_id: int) -> CameraModelWithRelations | None:
        with write_session() as sess:
            try:
                camera = sess.exec(
                    select(CameraEntity).where(CameraEntity.id == camera_id)
                ).first()

                return CameraModelWithRelations.model_validate(
                    camera.to_dict(
                        include_relationships=True
                    )
                )
            except Exception as e:
                Logger.err(str(e))

    @classmethod
    def add_camera(cls, model: CameraBaseModel):
        with write_session() as sess:
            try:
                camera = cls.prepare_camera(model, CameraEntity())
                sess.add(camera)
                sess.commit()
                sess.refresh(camera)

                return CameraModelWithRelations.model_validate(
                    camera.to_dict(
                        include_relationships=True
                    )
                )
            except Exception as e:
                Logger.err(str(e))

    @classmethod
    def update_camera(cls, model: CameraBaseModel):
        with write_session() as sess:
            try:
                cam = cls.get_camera(model.id)
                camera_orm = sess.get(CameraEntity, cam.id)
                camera = cls.prepare_camera(model, camera_orm)
                sess.add(camera)

                return CameraModelWithRelations.model_validate(
                    camera.to_dict(
                        include_relationships=True
                    )
                )
            except Exception as e:
                Logger.err(str(e))

    @classmethod
    def prepare_camera(cls, model: CameraBaseModel, target: CameraEntity):
        camera = target
        try:
            camera.storage_id = model.storage_id
            camera.name = model.name
            camera.active = model.active
            camera.alerts = model.active
            camera.record = model.record
            camera.record_mode = model.record_mode.value
            camera.record_duration = model.record_duration
            camera.delete_after = model.delete_after
            if model.protocol is not CameraProtocolEnum.USB:
                camera.ip = model.ip
                camera.port = model.port
            camera.protocol = model.protocol
            if model.change_credentials:
                camera.username = model.username
                if model.password is not None:
                    ecosystem = get_ecosystem()
                    camera.password = ecosystem.crypto.encrypt(model.password)
                else:
                    model.password = None
            camera.primary = model.primary
            camera.secondary = model.secondary
            return camera

        except Exception as e:
            Logger.err(f"[{camera.name}] prepare_camera error - {e}")
