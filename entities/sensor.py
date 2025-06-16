from datetime import datetime
from typing import Optional, Union, TYPE_CHECKING

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field, Relationship

from entities.device import Device
from entities.mixins.created_updated import TimeStampMixin
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum

if TYPE_CHECKING:
    from entities.sensor_history import SensorHistory


class Sensor(SQLModel, TimeStampMixin, table=True):
    __tablename__ = 'device_sensors'
    id: int | None = Field(default=None, primary_key=True)
    device_id: int | None = Field(default=None, foreign_key="devices.id")
    device: Device | None = Relationship(back_populates="sensors")
    type: MqttSensorTypeEnum = Field(nullable=True)
    identifier: str = Field(unique=True, index=True)
    name: str = Field(nullable=True)
    visible_name: str = Field(nullable=True)
    options: Optional[dict] = Field(sa_column=Column(JSON, nullable=True))
    value: str | None = Field(nullable=True)
    photo: str = Field(nullable=True)
    history: list["SensorHistory"] = Relationship(back_populates="sensor")
    last_sync: datetime = Field(nullable=True)

    # class Config:
    #     arbitrary_types_allowed = True
