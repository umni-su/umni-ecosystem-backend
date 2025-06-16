from pydantic import BaseModel


class MqttDioModel(BaseModel):
    level: int
    index: int
