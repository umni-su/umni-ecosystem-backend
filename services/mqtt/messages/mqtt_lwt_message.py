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

from classes.logger.logger import Logger
from database.session import write_session
from entities.device import DeviceEntity
from services.mqtt.messages.base_message import BaseMessage


class MqttLwtMessage(BaseMessage):

    def save(self):
        if self.has_device:
            with write_session() as session:
                try:
                    device = session.get(DeviceEntity, self.topic.device_model.id)
                    device.online = False
                    session.add(device)
                except Exception as e:
                    Logger.err(f'MqttLwtMessage->save: error with code: {str(e)}')

    def sensor_value(self):
        return None
