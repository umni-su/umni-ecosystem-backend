from pydantic import BaseModel


class MqttCnfOwModel(BaseModel):
    label: str | None = None
    sn: str
    active: bool
