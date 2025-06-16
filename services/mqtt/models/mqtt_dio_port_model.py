from pydantic import BaseModel


class MqttDioPort(BaseModel):
    label: str | None = None
    index: int
    order: int
    state: int
