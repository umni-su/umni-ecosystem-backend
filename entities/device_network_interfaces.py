from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from entities.mixins.created_updated import TimeStampMixin
from entities.device import Device


class DeviceNetworkInterface(SQLModel, TimeStampMixin, table=True):
    __tablename__ = 'device_network_interfaces'
    id: int | None = Field(default=None, primary_key=True)
    device_id: int | None = Field(default=None, foreign_key="devices.id")
    device: Device | None = Relationship(back_populates="network_interfaces")
    name: str = Field(nullable=False)
    mac: str = Field(unique=True, index=True)
    ip: str = Field(max_length=15)
    mask: str = Field(max_length=15)
    gw: str = Field(max_length=15)
    last_sync: datetime = Field(nullable=True)
