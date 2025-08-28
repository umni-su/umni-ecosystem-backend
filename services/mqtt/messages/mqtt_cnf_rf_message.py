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

from classes.logger.logger import Logger
from database.session import write_session
from services.mqtt.messages.base_message import BaseMessage
from services.mqtt.models.mqtt_rf_item_model import MqttRfItemModel
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum
from services.mqtt.topics.mqtt_topic_enum import MqttTopicEnum


class MqttCnfRfMessage(BaseMessage):
    model: RootModel[List[MqttRfItemModel]]

    def prepare_message(self):
        self.model = RootModel[List[MqttRfItemModel]].model_validate_json(self.original_message)

    def save(self):
        with write_session() as session:
            try:
                for rf in self.model.root:
                    identifier = '.'.join([
                        'dev',
                        str(self.topic.device_model.id),
                        MqttTopicEnum.RF433,
                        str(rf.serial)
                    ])
                    sensor = self.get_or_new_sensor(identifier)
                    sensor.device_id = self.topic.device_model.id
                    sensor.identifier = identifier
                    sensor.name = rf.label
                    sensor.type = MqttSensorTypeEnum.RF433.value
                    sensor.options = rf.model_dump()
                    sensor.last_sync = datetime.datetime.now()
                    sensor.value = str(rf.state)
                    session.add(sensor)
                session.commit()
                Logger.info(f'📟⚙️ [{self.topic.original_topic}] RF433 config saved successfully')
            except Exception as e:
                print(e)
