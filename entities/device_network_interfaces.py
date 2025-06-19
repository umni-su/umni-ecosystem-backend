from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from entities.mixins.created_updated import TimeStampMixin
from entities.device import Device
from entities.mixins.id_column import IdColumnMixin


class DeviceNetworkInterfaceBase:
    device_id: int | None = Field(default=None, foreign_key="devices.id")
    name: str = Field(nullable=False)
    mac: str = Field(unique=True, index=True)
    ip: str = Field(max_length=15)
    mask: str = Field(max_length=15)
    gw: str = Field(max_length=15)
    last_sync: datetime = Field(nullable=True)


class DeviceNetworkInterface(TimeStampMixin, DeviceNetworkInterfaceBase, IdColumnMixin, table=True):
    __tablename__ = 'device_network_interfaces'
    device: Device | None = Relationship(back_populates="network_interfaces")
