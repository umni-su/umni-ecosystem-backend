import datetime

from pydantic_core import ValidationError

from classes.logger import Logger
from database.database import write_session
from entities.device import Device
from entities.device_network_interfaces import DeviceNetworkInterface
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
            print(e)

    def save(self):
        try:
            with write_session() as session:
                if self.topic.device_model is not None:
                    device = session.get(Device, self.topic.device_model.id)
                else:
                    device = Device()
                device.name = self.model.name
                device.type = self.model.type
                device.fw_ver = self.model.systeminfo.fw_ver
                device.free_heap = self.model.systeminfo.free_heap
                device.total_heap = self.model.systeminfo.total_heap
                device.uptime = self.model.systeminfo.uptime
                device.last_sync = datetime.datetime.now()
                device.online = True
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

                Logger.info(f'📟💡 [Device ID{device.id} / {device.name}] - registration success')

        except Exception as e:
            print(e)
