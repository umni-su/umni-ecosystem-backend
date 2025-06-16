from datetime import datetime

from pydantic import BaseModel

from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum


class SensorModel(BaseModel):
    id: int | None = None
    device_id: int | None = None
    type: MqttSensorTypeEnum | None = None
    identifier: str
    name: str | None = None
    visible_name: str | None = None
    options: dict | None = None
    value: str | None = None
    photo: str | None = None
    last_sync: datetime | None = None
