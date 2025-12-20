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

from pydantic_core import ValidationError

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.device import DeviceEntity
from entities.device_network_interfaces import DeviceNetworkInterface
from models.enums.device_model_source import DeviceModelSource
from models.enums.log_code import LogCode
from models.log_model import LogEntityCode
from services.mqtt.messages.base_message import BaseMessage
from services.mqtt.models.mqtt_register_model import MqttRegisterModel

'''
Example struct
device/umni595804/register
 {
     "name":"umni595804",
     "type":20,
     "systeminfo":
     {
         "uptime":5224182,
         "free_heap":102376,
         "total_heap":308384,
         "fw_ver":"1.0.16",
         "idf_ver":"v5.4-dirty",
         "netif":[
             {
                 "name":"Ethernet",
                 "mac":"f2:24:f9:59:58:04",
                 "ip":"192.168.88.37",
                 "mask":"255.255.252.0",
                 "gw":"192.168.88.9"
             }
         ]
     }
 }
'''


class MqttRegisterMessage(BaseMessage):
    name: str
    type: int
    model: MqttRegisterModel

    def prepare_message(self):
        try:
            self.model = MqttRegisterModel.model_validate_json(self.original_message)
        except ValidationError as e:
            Logger.err(f'MqttRegisterMessage->prepare_message() {str(e)}', LoggerType.DEVICES)

    def save(self):
        try:
            with write_session() as session:
                if self.topic.device_model is not None:
                    device = session.get(DeviceEntity, self.topic.device_model.id)
                else:
                    device = DeviceEntity()
                device.name = self.model.name
                device.type = self.model.type
                device.fw_ver = self.model.systeminfo.fw_ver
                device.free_heap = self.model.systeminfo.free_heap
                device.total_heap = self.model.systeminfo.total_heap
                device.uptime = self.model.systeminfo.uptime
                device.last_sync = datetime.datetime.now()
                device.online = True
                device.source = DeviceModelSource.SERVICE_MQTT.value
                session.add(device)
                session.commit()
                session.refresh(device)

                # Find network interfaces
                for netif in self.model.systeminfo.netif:
                    ni = DeviceNetworkInterface()
                    for device_netif in device.network_interfaces:
                        if device_netif.mac == netif.mac:
                            ni = device_netif
                            break
                    ni.mac = netif.mac
                    ni.name = netif.name
                    ni.ip = netif.ip
                    ni.mask = netif.mask
                    ni.gw = netif.gw
                    ni.device = device
                    ni.last_sync = datetime.datetime.now()
                    session.add(ni)
                    # if founded is not None:
                    #     ni = founded
                session.commit()

                Logger.info(
                    f'📟💡 [Device ID{device.id} / {device.name}] - registration success',
                    LoggerType.DEVICES,
                    with_db=True,
                    entity_code=LogEntityCode(
                        id=device.id,
                        code=LogCode.DEVICE_REGISTERED,
                    )
                )

        except Exception as e:
            Logger.err(f'MqttRegisterMessage->save() {str(e)}', LoggerType.DEVICES)
