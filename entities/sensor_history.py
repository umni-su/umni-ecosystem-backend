from sqlmodel import SQLModel, Field, Relationship

from entities.mixins.created_updated import TimeStampMixin
from entities.sensor import Sensor


class SensorHistory(SQLModel, TimeStampMixin, table=True):
    __tablename__ = 'device_sensors_history'
    id: int | None = Field(default=None, primary_key=True)
    sensor_id: int | None = Field(default=None, foreign_key="device_sensors.id")
    sensor: Sensor | None = Relationship(back_populates="history")
    value: str = Field(nullable=True)
