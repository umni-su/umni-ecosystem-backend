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

from typing import TYPE_CHECKING, Optional

from entities.camera import CameraEntity
from entities.enums.event_priority_enum import EventPriorityEnum
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship, Column
from sqlalchemy.types import JSON, Boolean
from sqlalchemy.sql import false

if TYPE_CHECKING:
    from entities.camera_event import CameraEventEntity


class CameraAreaEntityBase:
    camera_id: int = Field(
        nullable=False,
        index=True,
        foreign_key="cameras.id"
    )
    name: str = Field(
        nullable=False
    )
    priority: Optional[int] = Field(
        nullable=False,
        default=EventPriorityEnum.ALERT
    )
    active: bool = Field(
        sa_column=Column(
            Boolean,
            index=True,
            nullable=False,
            server_default=false())
    )
    points: list[list[int]] = Field(
        sa_column=Column(
            JSON,
            nullable=True
        )
    )
    color: str = Field(
        nullable=False,
        default='#2D90B869'
    )
    options: Optional[dict] = Field(
        sa_column=Column(
            JSON,
            nullable=True
        )
    )


class CameraAreaEntity(
    TimeStampMixin,
    CameraAreaEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'camera_areas'
    camera: CameraEntity | None = Relationship(
        # sa_relationship_kwargs=dict(lazy="selectin"),
        back_populates="areas")

    events: list["CameraEventEntity"] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin",
            cascade="all, delete-orphan"
        ),
        back_populates="area",
    )
