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
from classes.logger.logger_types import LoggerType
from config.dependencies import get_ecosystem
from classes.logger.logger import Logger
from database.session import write_session
from entities.camera import CameraEntity
from entities.enums.camera_protocol_enum import CameraProtocolEnum
from models.camera_model import CameraBaseModel, CameraModelWithRelations
from repositories.base_repository import BaseRepository
from sqlmodel import select


class CameraRepository(BaseRepository):
    entity_class = CameraEntity
    model_class = CameraModelWithRelations

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
                Logger.err(str(e), LoggerType.APP)

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
            Logger.err(f"[{camera.name}] prepare_camera error - {e}", LoggerType.APP)
