from pydantic import BaseModel


class MqttAiModel(BaseModel):
    channel: int
    value: int
    voltage: int
