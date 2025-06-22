from datetime import datetime

from pydantic import BaseModel

from models.sensor_history_model import SensorHistoryModel
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum
from fastapi import UploadFile


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


class SensorUpdateModel(BaseModel):
    id: int
    name: str | None = None
    cover: UploadFile | None = None


class SensorModelWithHistory(SensorModel):
    history: list[SensorHistoryModel]
