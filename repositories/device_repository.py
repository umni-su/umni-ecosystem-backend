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

from fastapi import UploadFile
from sqlalchemy.orm import contains_eager
from sqlmodel import select, col

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.storages.device_storage import device_storage
from classes.storages.upload_validator import UploadValidator
from database.session import write_session
from entities.device import DeviceEntity
from entities.sensor_entity import SensorEntity
from models.device_model import DeviceUpdateModel
from models.device_model_relations import DeviceModelWithRelations
from repositories.base_repository import BaseRepository


class DeviceRepository(BaseRepository):
    entity_class = DeviceEntity
    model_class = DeviceModelWithRelations

    @classmethod
    def get_devices(cls):
        with write_session() as sess:
            try:
                devices_orm = sess.exec(
                    select(DeviceEntity).order_by(
                        col(DeviceEntity.id).desc()
                    )
                ).all()
                return [
                    DeviceModelWithRelations.model_validate(
                        _d.to_dict(
                            include_relationships=True
                        )
                    ) for _d in devices_orm
                ]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_device(cls, device_id: int):
        with write_session() as sess:
            try:
                q = (
                    select(DeviceEntity)
                    .join(col(DeviceEntity.sensors))
                    .where(col(DeviceEntity.id) == device_id)
                    .order_by(col(SensorEntity.name).asc())
                    .options(contains_eager(DeviceEntity.sensors))  # type: ignore
                )
                device_orm = sess.exec(q).first()
                return DeviceModelWithRelations.model_validate(
                    device_orm.to_dict(
                        include_relationships=True
                    )
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def update_device(cls, device_id: int, model: DeviceUpdateModel):
        with write_session() as sess:
            try:
                device = sess.get(DeviceEntity, device_id)
                device.title = model.title
                sess.add(device)
                sess.commit()
                sess.refresh(device)

                return DeviceModelWithRelations.model_validate(
                    device.to_dict(
                        include_relationships=True
                    )
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def upload_device_cover(cls, device_id: int, cover: UploadFile):
        with write_session() as sess:
            try:
                validator = UploadValidator(cover)
                validator.is_image().max_size(5).validate()

                device = sess.get(DeviceEntity, device_id)
                photo = device_storage.cover_upload(
                    device=device,
                    file=cover
                )
                device.photo = photo
                sess.add(device)
                sess.commit()
                sess.refresh(device)

                return DeviceModelWithRelations.model_validate(
                    device.to_dict(
                        include_relationships=True
                    )
                )

            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
