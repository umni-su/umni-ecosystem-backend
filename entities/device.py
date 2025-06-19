from datetime import datetime

from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship
from entities.mixins.created_updated import TimeStampMixin

from typing import TYPE_CHECKING
from entities.mixins.id_column import IdColumnMixin

if TYPE_CHECKING:
    from entities.device_network_interfaces import DeviceNetworkInterface
    from entities.sensor import Sensor


class DeviceBase:
    name: str = Field(index=True, unique=True)
    title: str | None = Field(nullable=True)
    description: str | None = Field(nullable=True)
    photo: str | None = Field(nullable=True)
    type: int | None = Field(nullable=True)
    online: bool = Field(default=False)
    uptime: int | None = Field(nullable=True)
    free_heap: int | None = Field(nullable=True)
    total_heap: int | None = Field(nullable=True)
    fw_ver: str | None = Field(nullable=True, max_length=10)
    last_sync: datetime | None = Field(nullable=True)


class Device(TimeStampMixin, DeviceBase, IdColumnMixin, table=True):
    __tablename__ = 'devices'
    sensors: list["Sensor"] = Relationship(back_populates="device")
    network_interfaces: list["DeviceNetworkInterface"] = Relationship(back_populates="device")
