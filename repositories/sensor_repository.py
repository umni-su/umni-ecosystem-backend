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
from typing import Optional, Union

from sqlmodel import select, col, or_
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException

from classes.events.event_bus import event_bus
from classes.events.event_types import EventType
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.storages.device_storage import device_storage
from database.session import write_session, read_session
from entities.device import DeviceEntity
from entities.sensor_entity import SensorEntity
from entities.sensor_history import SensorHistory
from models.sensor_model import SensorUpdateModel, SensorModel, SensorModelWithDevice, SensorCreateModel, \
    SensorUpdateModelUi
from repositories.base_repository import BaseRepository
from starlette.status import HTTP_404_NOT_FOUND

from repositories.sensor_history_repository import SensorHistoryRepository


class SensorRepository(BaseRepository):
    entity_class = SensorEntity
    model_class = SensorModelWithDevice

    @classmethod
    def _return_sensor_with_relations(cls, sensor_orm: Optional[SensorEntity]):
        if sensor_orm is not None:
            return SensorModelWithDevice.model_validate(
                sensor_orm.to_dict(
                    include_relationships=True
                )
            )
        return None

    @classmethod
    def get_sensor(cls, sensor_id: int):
        with read_session() as sess:
            try:
                q = select(SensorEntity).where(SensorEntity.id == sensor_id)
                sensor_orm = sess.exec(q).first()
                if sensor_orm:
                    sess.refresh(sensor_orm)
                return cls._return_sensor_with_relations(sensor_orm)
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_sensor_by_device_and_identifier(cls, device_id: int, identifier: str):
        with write_session() as sess:
            try:
                q = select(SensorEntity).where(
                    SensorEntity.device_id == device_id
                ).where(
                    SensorEntity.identifier == identifier
                )
                sensor_orm = sess.exec(q).first()
                return cls._return_sensor_with_relations(sensor_orm)
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def update_sensor_value(cls, sensor_id: int, value: Optional[Union[int | float | str]]):
        with write_session() as sess:
            try:
                sensor = sess.get(SensorEntity, sensor_id)
                if isinstance(sensor, SensorEntity):
                    sensor.value = value
                    sess.add(sensor)

                    last_record = SensorHistoryRepository.get_last_record(sensor)
                    if last_record is None or last_record.value != str(
                            value):  # Todo map_type last_record.value in model by type
                        history = SensorHistory()
                        history.sensor_id = sensor_id
                        history.value = value
                        sess.add(history)

                    sess.commit()

                    sensor_model = cls._return_sensor_with_relations(sensor)
                    if sensor_model is not None:
                        event_bus.publish(
                            event_type=EventType.SENSOR_CHANGE_STATE,
                            sensor=sensor_model
                        )

                    return sensor_model
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def create_sensor(cls, model: SensorCreateModel):
        with write_session() as sess:
            try:
                sensor = SensorEntity.model_validate(
                    model.model_dump()
                )
                sess.add(sensor)
                sess.commit()
                sess.refresh(sensor)
                return cls._return_sensor_with_relations(sensor)
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def update_sensor(cls, model: SensorUpdateModelUi):
        with write_session() as sess:
            try:
                sensor = sess.get(SensorEntity, model.id)
                if isinstance(sensor, SensorEntity):
                    sensor.visible_name = model.visible_name

                    if model.photo is not None:
                        photo = device_storage.sensor_cover_upload(
                            sensor=sensor,
                            file=model.photo
                        )
                        sensor.photo = photo

                    sess.add(sensor)
                    sess.commit()
                    sess.refresh(sensor)

                    return SensorModel.model_validate(
                        sensor.to_dict()
                    )
                else:
                    raise HTTPException(
                        status_code=HTTP_404_NOT_FOUND, detail="Sensor not found"
                    )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def find_sensors(cls, term: str | None = None):
        with write_session() as sess:
            try:
                query = select(SensorEntity).options(
                    selectinload(SensorEntity.device)
                ).join(
                    SensorEntity.device
                )
                if term is not None:
                    query = query.where(
                        or_(
                            col(DeviceEntity.name).ilike(f"%{term}%"),
                            col(DeviceEntity.title).ilike(f"%{term}%"),
                            col(SensorEntity.name).ilike(f"%{term}%"),
                            col(SensorEntity.identifier).ilike(f"%{term}%"),
                            col(SensorEntity.visible_name).ilike(f"%{term}%"),
                        )
                    )
                else:
                    query = query.limit(50)
                sensors = sess.exec(query).all()
                return [
                    SensorModelWithDevice.model_validate(
                        s.to_dict(
                            include_relationships=True
                        )
                    ) for s in sensors
                ]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                raise HTTPException(
                    status_code=500, detail="Error fetching sensors"
                )
