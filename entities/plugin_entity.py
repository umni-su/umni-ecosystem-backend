# Copyright (C) 2025 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Optional, Dict, Any
from sqlmodel import Field, JSON
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class PluginEntityBase:
    name: str = Field(
        nullable=False,
        index=True
    )

    display_name: str = Field(
        nullable=False
    )

    version: str = Field(
        nullable=False,
        default="1.0.0"
    )

    description: Optional[str] = Field(
        default=None,
        nullable=True
    )

    author: Optional[str] = Field(
        default=None,
        nullable=True
    )

    url: Optional[str] = Field(
        default=None,
        nullable=True
    )

    active: bool = Field(
        default=False,
        nullable=False,
        index=True
    )

    status: str = Field(
        default="stopped",
        nullable=False  # stopped|running|error
    )

    config: Optional[Dict[str, Any]] = Field(
        sa_type=JSON,
        default=None,
        nullable=True
    )

    error_message: Optional[str] = Field(
        default=None,
        nullable=True
    )


class PluginEntity(
    TimeStampMixin,
    PluginEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'plugins'
