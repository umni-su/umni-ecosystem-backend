from typing import List

from pydantic import BaseModel

from services.mqtt.models.mqtt_netif_model import MqttNetifModel


class MqttSysteminfoModel(BaseModel):
    uptime: int
    free_heap: int
    total_heap: int
    fw_ver: str
    idf_ver: str
    netif: List[MqttNetifModel] = []
