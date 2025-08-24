from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship

from entities.device import Device
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin

if TYPE_CHECKING:
    from entities.sensor_history import SensorHistory


class SensorBase:
    device_id: int | None = Field(
        index=True,
        default=None,
        foreign_key="devices.id"
    )
    type: Optional[int] = Field(
        index=True,
        nullable=True,
        description=" -> MqttSensorTypeEnum"
    )
    identifier: str = Field(
        unique=True,
        index=True
    )
    name: str = Field(
        nullable=True
    )
    visible_name: str = Field(
        nullable=True
    )
    options: Optional[dict] = Field(
        sa_column=Column(
            JSON, nullable=True
        )
    )
    value: str | None = Field(
        nullable=True
    )
    photo: str = Field(
        nullable=True
    )
    last_sync: datetime = Field(
        index=True,
        nullable=True
    )


class Sensor(
    TimeStampMixin,
    SensorBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'device_sensors'

    device: Device | None = Relationship(
        back_populates="sensors"
    )
    history: list["SensorHistory"] = Relationship(
        back_populates="sensor"
    )
