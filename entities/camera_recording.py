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
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin

if TYPE_CHECKING:
    from entities.camera import CameraEntity
    from entities.camera_event import CameraEventEntity


class CameraRecordingEntity(
    TimeStampMixin,
    IdColumnMixin,
    table=True
):
    __tablename__ = "camera_recordings"

    camera_id: int = Field(
        index=True,
        foreign_key="cameras.id"
    )
    start: datetime = Field(
        index=True,
        default_factory=datetime.now,
        nullable=False
    )
    end: datetime = Field(
        index=True,
        nullable=True
    )
    duration: Optional[float] = None
    path: Optional[str] = None

    camera: "CameraEntity" = Relationship(
        # sa_relationship_kwargs=dict(lazy="selectin"),
        back_populates="recordings")

    events: list["CameraEventEntity"] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin",
            cascade="all, delete-orphan"
        ),
        back_populates="recording"
    )
