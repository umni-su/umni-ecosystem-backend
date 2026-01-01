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

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class PermissionCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: str


class RoleCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    is_default: bool = False
    is_system: bool = False
    permission_codes: List[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    permission_codes: Optional[List[str]] = None


class UserRoleAssign(BaseModel):
    action: str
    role_code: str


class PermissionModel(BaseModel):
    """Упрощенная модель разрешения без рекурсивных связей"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    category: str


class RoleModel(BaseModel):
    """Упрощенная модель роли"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    is_default: bool = False
    is_system: bool = False


class RoleModelWithPermissions(RoleModel):
    """Роль с разрешениями"""
    permissions: List[PermissionModel] = Field(default_factory=list)


class UserRoleModel(BaseModel):
    """Упрощенная модель связи пользователь-роль"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role_id: int
    role: RoleModelWithPermissions | None = None
