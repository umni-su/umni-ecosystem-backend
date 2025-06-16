from pydantic import BaseModel

from services.mqtt.models.mqtt_systeminfo_model import MqttSysteminfoModel


class MqttRegisterModel(BaseModel):
    name: str
    type: int
    systeminfo: MqttSysteminfoModel
