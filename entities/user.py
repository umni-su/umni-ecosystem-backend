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

from sqlmodel import Field

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class UserEntityBase:
    username: str = Field(
        index=True,
        unique=True
    )
    password: str = Field(
        index=True
    )
    email: str = Field(
        index=True,
        unique=True
    )
    firstname: str = Field(
        nullable=True
    )
    lastname: str = Field(
        nullable=True
    )


class UserEntity(
    TimeStampMixin,
    UserEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'users'
