from pydantic import BaseModel


class MqttRfItemModel(BaseModel):
    serial: int
    label: str | None = None
    type: int | None = None
    alarm: bool
    state: int
