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
from enum import StrEnum

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.device import DeviceEntity
from services.mqtt.messages.base_message import BaseMessage
from services.mqtt.models.mqtt_lwt_model import MqttLwtMessageState, MqttLwtModel


class MqttLwtMessage(BaseMessage):
    def prepare_message(self):
        self.model: MqttLwtModel = MqttLwtModel.model_validate_json(self.original_message)

    def save(self):
        if self.has_device:
            with write_session() as session:
                try:
                    device = session.get(DeviceEntity, self.topic.device_model.id)
                    device.online = self.model.state == MqttLwtMessageState.ONLINE.value
                    session.add(device)
                    Logger.info(f'Device {device.id} is: {self.model.state.name}', LoggerType.DEVICES)
                except Exception as e:
                    Logger.err(f'MqttLwtMessage->save: error with code: {str(e)}', LoggerType.DEVICES)

    def sensor_value(self):
        return None
