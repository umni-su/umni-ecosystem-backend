from pydantic import BaseModel


class MqttNtcModel(BaseModel):
    channel: int
    temp: float
