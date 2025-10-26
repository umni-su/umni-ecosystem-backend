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

from typing import Optional, Dict, Any

from sqlmodel import Field, Column, Boolean
from sqlalchemy.types import JSON
from sqlalchemy.sql import true

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class NotificationEntityBase:
    name: str = Field(
        nullable=False
    )
    type: Optional[int] = Field(
        index=True,
        nullable=False,
        description=" -> NotificationTypeEnum"
    )
    active: bool = Field(
        sa_column=Column(
            Boolean,
            index=True,
            nullable=False,
            server_default=true()
        )
    )
    options: Optional[Dict[str, Any]] = Field(
        sa_type=JSON,
        default=None,
        nullable=True,
        description=" -> NotificationOptionsBaseModel"
    )


class NotificationEntity(
    TimeStampMixin,
    NotificationEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'notifications'
