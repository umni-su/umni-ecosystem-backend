from pydantic import BaseModel


class MqttOwModel(BaseModel):
    sn: str
    temp: float
