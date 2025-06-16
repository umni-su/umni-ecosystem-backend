from pydantic import BaseModel


class MqttCnfAnalogPortModel(BaseModel):
    type: int
    channel: int
    en: bool
    label: str | None = None


class MqttCnfAnalogPortsModel(BaseModel):
    ntc1: MqttCnfAnalogPortModel
    ntc2: MqttCnfAnalogPortModel
    ai1: MqttCnfAnalogPortModel
    ai2: MqttCnfAnalogPortModel
