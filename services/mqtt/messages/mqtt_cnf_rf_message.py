import datetime

from sqlmodel import select

import database.database as db
from typing import List
from pydantic import RootModel

from entities.sensor import Sensor
from services.mqtt.messages.base_message import BaseMessage
from services.mqtt.models.mqtt_rf_item_model import MqttRfItemModel
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum
from services.mqtt.topics.mqtt_topic_enum import MqttTopicEnum


class MqttCnfRfMessage(BaseMessage):
    model: RootModel[List[MqttRfItemModel]]

    def prepare_message(self):
        self.model = RootModel[List[MqttRfItemModel]].model_validate_json(self.original_message)

    def save(self):
        with db.get_separate_session() as session:
            try:
                for rf in self.model.root:
                    identifier = '.'.join([
                        'dev',
                        str(self.topic.device_entity.id),
                        MqttTopicEnum.RF433,
                        str(rf.serial)
                    ])
                    sensor = self.get_or_new_sensor(identifier)
                    sensor.device = self.topic.device_entity
                    sensor.identifier = identifier
                    sensor.name = rf.label
                    sensor.type = MqttSensorTypeEnum.RF433
                    sensor.options = rf.model_dump()
                    sensor.last_sync = datetime.datetime.now()
                    sensor.value = str(rf.state)
                    session.add(sensor)
                session.commit()
            except Exception as e:
                print(e)
