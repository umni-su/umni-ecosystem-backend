from datetime import datetime
from typing import Optional, Union, TYPE_CHECKING

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field, Relationship

from entities.device import Device
from entities.mixins.created_updated import TimeStampMixin
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum
from entities.mixins.id_column import IdColumnMixin

if TYPE_CHECKING:
    from entities.sensor_history import SensorHistory


class SensorBase:
    device_id: int | None = Field(default=None, foreign_key="devices.id")
    type: MqttSensorTypeEnum = Field(nullable=True)
    identifier: str = Field(unique=True, index=True)
    name: str = Field(nullable=True)
    visible_name: str = Field(nullable=True)
    options: Optional[dict] = Field(sa_column=Column(JSON, nullable=True))
    value: str | None = Field(nullable=True)
    photo: str = Field(nullable=True)
    last_sync: datetime = Field(nullable=True)


class Sensor(TimeStampMixin, SensorBase, IdColumnMixin, table=True):
    __tablename__ = 'device_sensors'
    device: Device | None = Relationship(back_populates="sensors")
    history: list["SensorHistory"] = Relationship(back_populates="sensor")

    # class Config:
    #     arbitrary_types_allowed = True
