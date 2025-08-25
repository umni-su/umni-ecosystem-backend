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

from sqlmodel import Session

from classes.logger import Logger
from database.session import write_session
from services.mqtt.messages.base_message import BaseMessage
from services.mqtt.models.mqtt_dio_cnf_model import MqttDioCngModel
from services.mqtt.models.mqtt_dio_port_model import MqttDioPort
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum
from services.mqtt.topics.mqtt_topic_enum import MqttTopicEnum


class MqttCnfDioMessage(BaseMessage):
    model: MqttDioCngModel

    def prepare_message(self):
        self.model = MqttDioCngModel.model_validate_json(self.original_message)

    def create_update(self, session: Session, port: MqttDioPort, sensor_type: MqttSensorTypeEnum):
        _type = MqttTopicEnum.INP
        if sensor_type == MqttSensorTypeEnum.RELAY:
            _type = MqttTopicEnum.REL
        identifier = '.'.join([
            'dev',
            str(self.topic.device_model.id),
            _type,
            str(port.index)
        ])
        sensor = self.get_or_new_sensor(identifier)
        sensor.device_id = self.topic.device_model.id
        sensor.identifier = identifier
        sensor.name = port.label
        sensor.type = sensor_type.value
        sensor.value = str(port.state)
        sensor.last_sync = datetime.datetime.now()
        sensor.options = port.model_dump()
        session.add(sensor)

    def save(self):
        with write_session() as session:
            try:
                for di in self.model.di:
                    self.create_update(session, di, MqttSensorTypeEnum.INPUT)
                for do in self.model.do:
                    self.create_update(session, do, MqttSensorTypeEnum.RELAY)
                session.commit()

                Logger.info(
                    f'📟⚙️ [{self.topic.original_topic}] DIO config saved successfully')
            except Exception as e:
                print(e)
