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

from sqlmodel import SQLModel, Field, Relationship
from entities.mixins.created_updated import TimeStampMixin
from entities.device import DeviceEntity
from entities.mixins.id_column import IdColumnMixin


class DeviceNetworkInterfaceBase:
    device_id: int | None = Field(
        index=True,
        default=None,
        foreign_key="devices.id"
    )
    name: str = Field(
        nullable=False
    )
    mac: str = Field(
        unique=True,
        index=True
    )
    ip: str = Field(
        max_length=15
    )
    mask: str = Field(
        max_length=15
    )
    gw: str = Field(
        max_length=15
    )
    last_sync: datetime = Field(
        index=True,
        nullable=True
    )


class DeviceNetworkInterface(
    TimeStampMixin,
    DeviceNetworkInterfaceBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'device_network_interfaces'

    device: DeviceEntity | None = Relationship(
        back_populates="network_interfaces"
    )
