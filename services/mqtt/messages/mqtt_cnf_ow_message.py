import datetime
from typing import List
from pydantic import RootModel
from sqlmodel import select

import database.database as db
from entities.sensor import Sensor
from services.mqtt.messages.base_message import BaseMessage
from services.mqtt.models.mqtt_cnf_ow_model import MqttCnfOwModel
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum
from services.mqtt.topics.mqtt_topic_enum import MqttTopicEnum


class MqttCnfOwMessage(BaseMessage):
    model: RootModel[List[MqttCnfOwModel]]

    def prepare_message(self):
        self.model = RootModel[List[MqttCnfOwModel]].model_validate_json(self.original_message)

    def save(self):
        with db.get_separate_session() as session:
            try:
                for ow in self.model.root:
                    identifier = '.'.join([
                        'dev',
                        str(self.topic.device_entity.id),
                        MqttTopicEnum.OW,
                        ow.sn
                    ])
                    sensor = self.get_or_new_sensor(identifier)
                    sensor.identifier = identifier
                    sensor.name = ow.label
                    sensor.options = ow.model_dump()
                    sensor.device = self.topic.device_entity
                    sensor.last_sync = datetime.datetime.now()
                    sensor.type = MqttSensorTypeEnum.DS18B20
                    session.add(sensor)
                session.commit()
            except Exception as e:
                print(e)
