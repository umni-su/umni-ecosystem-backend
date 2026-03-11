#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON
from sqlmodel import Field, Relationship, BIGINT
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin

from entities.device_network_interfaces import DeviceNetworkInterface
from entities.sensor_entity import SensorEntity


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
    type: str | None = Field(
        index=True,
        nullable=True
    )
    source: str | None = Field(
        index=True,
        nullable=True
    )
    external_id: str | None = Field(
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
    capabilities: Optional[List[str]] = Field(
        sa_type=JSON,
        default=None,
        nullable=True,
    )


class DeviceEntity(
    TimeStampMixin,
    DeviceBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'devices'
    sensors: list["SensorEntity"] = Relationship(
        back_populates="device"
    )
    network_interfaces: list["DeviceNetworkInterface"] = Relationship(
        back_populates="device"
    )

    def __repr__(self):
        return f"<Device {self.name}>"
