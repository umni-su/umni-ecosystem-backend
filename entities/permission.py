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

from sqlmodel import Field, Relationship, UniqueConstraint
from typing import List, TYPE_CHECKING

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class PermissionEntityBase:
    code: str = Field(
        index=True,
        unique=True
    )  # Пример: "video:camera:create"
    name: str = Field(
        index=True
    )  # Человеческое название: "Создание камер"
    description: str | None = Field(
        default=None,
        nullable=True
    )
    category: str = Field(
        index=True
    )


class PermissionEntity(
    TimeStampMixin,
    PermissionEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'permissions'

    # Связи
    role_permissions: List["RolePermissionEntity"] = Relationship(
        back_populates="permission"
    )


class RoleEntityBase:
    name: str = Field(
        index=True,
        unique=True
    )
    code: str = Field(
        index=True,
        unique=True
    )  # Внутренний код: "admin", "video_manager", "viewer"
    description: str | None = Field(
        default=None,
        nullable=True
    )
    is_default: bool = Field(
        default=False
    )  # Роль по умолчанию для новых пользователей
    is_system: bool = Field(
        default=False
    )  # Системные роли нельзя удалять


class RoleEntity(
    TimeStampMixin,
    RoleEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'roles'

    # Связи
    role_permissions: List["RolePermissionEntity"] = Relationship(
        back_populates="role"
    )
    user_roles: List["UserRoleEntity"] = Relationship(
        back_populates="role"
    )


class RolePermissionEntity(
    IdColumnMixin,
    table=True
):
    """Связующая таблица Роль-Разрешение"""
    __tablename__ = 'role_permissions'

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role_id: int = Field(
        foreign_key="roles.id",
        primary_key=True
    )
    permission_id: int = Field(
        foreign_key="permissions.id",
        primary_key=True
    )

    role: RoleEntity = Relationship(
        back_populates="role_permissions"
    )
    permission: PermissionEntity = Relationship(
        back_populates="role_permissions"
    )


class UserRoleEntity(
    TimeStampMixin,
    IdColumnMixin,
    table=True
):
    """Связующая таблица Пользователь-Роль"""
    __tablename__ = 'user_roles'

    user_id: int = Field(
        foreign_key="users.id",
        primary_key=True
    )
    role_id: int = Field(
        foreign_key="roles.id",
        primary_key=True
    )

    # Связи
    user: "UserEntity" = Relationship(
        back_populates="roles"
    )
    role: RoleEntity = Relationship(
        back_populates="user_roles"
    )


# UserRoleEntity использует UserEntity как forward reference
from entities.user import UserEntity
