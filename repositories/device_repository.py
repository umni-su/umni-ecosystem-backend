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
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import contains_eager
from sqlmodel import select, col

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.storages.device_storage import device_storage
from classes.storages.upload_validator import UploadValidator
from database.session import write_session, read_session
from entities.device import DeviceEntity
from entities.device_network_interfaces import DeviceNetworkInterface
from entities.sensor_entity import SensorEntity
from models.device_model import DeviceUpdateModel, DeviceModel
from models.device_model_relations import DeviceModelWithRelations
from models.device_netif import DeviceNetifBase, DeviceNetif
from repositories.base_repository import BaseRepository


class DeviceRepository(BaseRepository):
    entity_class = DeviceEntity
    model_class = DeviceModelWithRelations

    @classmethod
    def get_devices(cls):
        with read_session() as sess:
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
        with read_session() as sess:
            try:
                q = (
                    select(DeviceEntity)
                    # .join(col(DeviceEntity.sensors))
                    .outerjoin(col(DeviceEntity.sensors))
                    .where(col(DeviceEntity.id) == device_id)
                    .order_by(col(SensorEntity.capability).asc())
                    .order_by(col(SensorEntity.identifier).asc())
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
    def get_device_by_name(cls, name: str):
        with read_session() as sess:
            try:
                q = select(DeviceEntity).where(
                    or_(
                        col(DeviceEntity.name) == name,
                        col(DeviceEntity.external_id) == name,
                    )
                )
                device_orm = sess.exec(q).first()
                if isinstance(device_orm, DeviceEntity):
                    return DeviceModelWithRelations.model_validate(
                        device_orm.to_dict(
                            include_relationships=True
                        )
                    )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_device_by_external_id(cls, external_id: str):
        with read_session() as sess:
            try:
                q = select(DeviceEntity).where(col(DeviceEntity.external_id) == external_id)
                device_orm = sess.exec(q).first()
                if isinstance(device_orm, DeviceEntity):
                    return DeviceModelWithRelations.model_validate(
                        device_orm.to_dict(
                            include_relationships=True
                        )
                    )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def update_device_meta(cls, device_id: int, meta: dict):
        """Обновить meta устройства (данные плагина)."""
        with write_session() as sess:
            try:
                device = sess.get(DeviceEntity, device_id)
                if device is None:
                    return None
                device.meta = meta
                sess.add(device)
                ### sess.commit()
                return DeviceModelWithRelations.model_validate(
                    device.to_dict(
                        include_relationships=True
                    )
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_device_by_plugin_id(cls, plugin_id: int):
        with read_session() as sess:
            try:
                q = select(DeviceEntity).where(col(DeviceEntity.plugin_id) == plugin_id)
                devices_orm = sess.exec(q).all()
                return [DeviceModelWithRelations.model_validate(
                    _d.to_dict(
                        include_relationships=True
                    )
                ) for _d in devices_orm]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def update_device_widget_type(cls, device_id: int, widget_type: Optional[str]):
        """Обновить тип виджета устройства (задаётся плагином при синхронизации)."""
        with write_session() as sess:
            try:
                device = sess.get(DeviceEntity, device_id)
                if device is None:
                    return None
                device.widget_type = widget_type
                sess.add(device)
                sess.commit()
                return DeviceModelWithRelations.model_validate(
                    device.to_dict(
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
                if model.widget_type is not None:
                    device.widget_type = model.widget_type
                if model.widget_name is not None:
                    device.widget_name = model.widget_name
                sess.add(device)
                ### sess.commit()

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
                ### sess.commit()

                return DeviceModelWithRelations.model_validate(
                    device.to_dict(
                        include_relationships=True
                    )
                )

            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def save_network_interface(self, ni: DeviceNetifBase):
        with write_session() as sess:
            try:
                db_ni = sess.exec(select(DeviceNetworkInterface).where(
                    col(DeviceNetworkInterface.device_id) == ni.device_id
                ).where(
                    col(DeviceNetworkInterface.mac) == ni.mac
                )).first()
                if not isinstance(db_ni, DeviceNetworkInterface):
                    db_ni = DeviceNetworkInterface()

                db_ni.device_id = ni.device_id
                db_ni.mac = ni.mac
                db_ni.name = ni.name
                db_ni.ip = ni.ip
                db_ni.mask = ni.mask
                db_ni.gw = ni.gw

                sess.add(db_ni)
                ### sess.commit()

                return DeviceNetif.model_validate(
                    db_ni.to_dict(
                        include_relationships=True
                    )
                )

            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
