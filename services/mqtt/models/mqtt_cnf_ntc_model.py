from pydantic import BaseModel


class MqttCnfNtcModel(BaseModel):
    type: int
    channel: int
    en: bool
    label: str | None = None
