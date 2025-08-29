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

import datetime

from sqlmodel import select

from classes.logger.logger_types import LoggerType
from config.dependencies import get_ecosystem
from classes.logger.logger import Logger
from database.session import write_session
from entities.configuration import ConfigurationKeys

from entities.sensor_entity import SensorEntity
from entities.sensor_history import SensorHistory
from repositories.sensor_history_repository import SensorHistoryRepository
from services.mqtt.messages.base_message import BaseMessage
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum


class MqttSensorMessage(BaseMessage):

    def save(self):
        ecosystem = get_ecosystem()
        if self.identifier is not None and self.has_device:
            with write_session() as session:
                founded = session.exec(
                    select(SensorEntity).where(SensorEntity.identifier == self.identifier)
                ).first()
                if isinstance(founded, SensorEntity):
                    try:
                        sensor = founded
                        sensor.device_id = self.topic.device_model.id
                        sensor.identifier = self.identifier
                        sensor.value = self.sensor_value()
                        session.add(sensor)
                        session.commit()
                        session.refresh(sensor)

                        delta: datetime.timedelta | None = None

                        last = SensorHistoryRepository.get_last_record(sensor)
                        if isinstance(last, SensorHistory):
                            delta_types = [
                                MqttSensorTypeEnum.AI,
                                MqttSensorTypeEnum.NTC,
                                MqttSensorTypeEnum.DS18B20,
                            ]
                            delta = datetime.datetime.now() - last.created
                            trigger = int(
                                ecosystem.config.get_setting(ConfigurationKeys.APP_DEVICE_SYNC_TIMEOUT).value)
                            # Logger.debug(f'{last.id} {last.sensor_id} Delta is {delta.seconds / 60}')
                            # Not check delta if relays inputs and buttons rf 433
                        if (delta is None or (delta.seconds / 60 >= trigger)) or (sensor.type not in delta_types):
                            history = SensorHistory()
                            history.value = sensor.value
                            history.sensor = sensor
                            session.add(history)
                            session.commit()
                            session.refresh(history)

                            Logger.info(
                                f"📟📄 [{self.topic.original_topic} / ID#{history.id} / {history.sensor.identifier}], type:{sensor.type}: {self.identifier} -> {self.sensor_value()}",
                                LoggerType.DEVICES)
                    except Exception as e:
                        Logger.err(f'MqttSensorMessage->save(): {str(e)}', LoggerType.DEVICES)

    def sensor_value(self):
        return None
