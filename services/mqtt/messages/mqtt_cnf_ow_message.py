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
from typing import List
from pydantic import RootModel

from classes.logger import Logger
from database.session import write_session
from services.mqtt.messages.base_message import BaseMessage
from services.mqtt.models.mqtt_cnf_ow_model import MqttCnfOwModel
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum
from services.mqtt.topics.mqtt_topic_enum import MqttTopicEnum


class MqttCnfOwMessage(BaseMessage):
    model: RootModel[List[MqttCnfOwModel]]

    def prepare_message(self):
        self.model = RootModel[List[MqttCnfOwModel]].model_validate_json(self.original_message)

    def save(self):
        with write_session() as session:
            try:
                for ow in self.model.root:
                    identifier = '.'.join([
                        'dev',
                        str(self.topic.device_model.id),
                        MqttTopicEnum.OW,
                        ow.sn
                    ])
                    sensor = self.get_or_new_sensor(identifier)
                    sensor.identifier = identifier
                    sensor.name = ow.label
                    sensor.options = ow.model_dump()
                    sensor.device_id = self.topic.device_model.id
                    sensor.last_sync = datetime.datetime.now()
                    sensor.type = MqttSensorTypeEnum.DS18B20.value
                    session.add(sensor)
                session.commit()

                Logger.info(f'📟⚙️ [{self.topic.original_topic}] 1-WIRE config saved successfully')
            except Exception as e:
                print(e)
