from enum import StrEnum

from pydantic import BaseModel


class MqttNetifType(StrEnum):
    ETHERNET = "Ethernet"


class MqttNetifModel(BaseModel):
    name: MqttNetifType
    mac: str
    ip: str | None = None
    mask: str | None = None
    gw: str | None = None
