from datetime import datetime

from sqlmodel import Field, Relationship, BIGINT

from entities.mixins.created_updated import TimeStampMixin

from typing import TYPE_CHECKING
from entities.mixins.id_column import IdColumnMixin

if TYPE_CHECKING:
    from entities.device_network_interfaces import DeviceNetworkInterface
    from entities.sensor import Sensor


class DeviceBase:
    name: str = Field(
        index=True,
        unique=True
    )
    title: str | None = Field(
        nullable=True
    )
    description: str | None = Field(
        nullable=True
    )
    photo: str | None = Field(
        nullable=True
    )
    type: int | None = Field(
        index=True,
        nullable=True
    )
    online: bool = Field(
        index=True,
        default=False
    )
    uptime: int | None = Field(
        default=None,
        nullable=True,
        sa_type=BIGINT
    )
    free_heap: int | None = Field(
        nullable=True,
        default=None,
    )
    total_heap: int | None = Field(
        default=None,
        nullable=True
    )
    fw_ver: str | None = Field(
        nullable=True,
        max_length=10
    )
    last_sync: datetime | None = Field(
        index=True,
        nullable=True
    )


class DeviceEntity(
    TimeStampMixin,
    DeviceBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'devices'
    sensors: list["Sensor"] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin"
        ),
        back_populates="device"
    )
    network_interfaces: list["DeviceNetworkInterface"] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin"
        ),
        back_populates="device"
    )

    def __repr__(self):
        return f"<Device {self.name}>"
