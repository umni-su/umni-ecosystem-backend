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

from typing import TYPE_CHECKING
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from entities.camera import CameraEntity


class StorageEntityBase:
    name: str = Field(
        nullable=True
    )
    path: str = Field(
        unique=True,
        nullable=True
    )
    active: bool = Field(
        index=True,
        default=True
    )


class StorageEntity(
    TimeStampMixin,
    StorageEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'storages'
    cameras: list["CameraEntity"] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin"
        ),
        back_populates="storage"
    )
