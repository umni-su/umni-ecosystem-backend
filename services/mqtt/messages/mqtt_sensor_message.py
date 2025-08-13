import datetime

from sqlmodel import select

import database.database as db
from classes.logger import Logger
from entities.configuration import ConfigurationKeys

from entities.sensor import Sensor
from entities.sensor_history import SensorHistory
from repositories.sensor_history_repository import SensorHistoryRepository
from services.mqtt.messages.base_message import BaseMessage
import classes.ecosystem as eco
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum


class MqttSensorMessage(BaseMessage):

    def __init__(self, topic: str, message: bytes):
        super().__init__(topic, message)

    # def prepare_message(self):
    #     print(self.model)
    #     self.model.model_validate_json(self.original_message)

    def save(self):

        if self.identifier is not None and self.has_device:
            with db.write_session() as session:
                founded = session.exec(
                    select(Sensor).where(Sensor.identifier == self.identifier)
                ).first()
                if isinstance(founded, Sensor):
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
                                eco.Ecosystem.config.get_setting(ConfigurationKeys.APP_DEVICE_SYNC_TIMEOUT).value)
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
                                f"📟📄 [{self.topic.original_topic} / ID#{history.id} / {history.sensor.identifier}], type:{sensor.type}: {self.identifier} -> {self.sensor_value()}")
                    except Exception as e:
                        Logger.err(e)

    def sensor_value(self):
        return None
