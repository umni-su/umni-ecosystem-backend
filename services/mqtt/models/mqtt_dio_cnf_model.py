from typing import List

from pydantic import BaseModel

from services.mqtt.models.mqtt_dio_port_model import MqttDioPort


class MqttDioCngModel(BaseModel):
    do: List[MqttDioPort]
    di: List[MqttDioPort]
