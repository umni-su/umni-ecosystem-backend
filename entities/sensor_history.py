from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from entities.sensor import Sensor


class SensorHistoryBase:
    sensor_id: int | None = Field(default=None, foreign_key="device_sensors.id")
    value: str = Field(nullable=True)


class SensorHistory(TimeStampMixin, SensorHistoryBase, IdColumnMixin, table=True):
    __tablename__ = 'device_sensors_history'
    sensor: Sensor | None = Relationship(back_populates="history")
