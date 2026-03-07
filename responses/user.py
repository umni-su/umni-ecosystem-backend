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
import re
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, ValidationInfo, field_validator

from classes.l10n.l10n import _
from models.mixins.password_mixin import PasswordMixin
from models.permission_model import UserRoleModel


class UserResponseOut(BaseModel):
    id: int
    username: str
    email: str
    firstname: str
    lastname: str
    is_superuser: bool
    is_active: bool
    roles: List[UserRoleModel] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class UserLoginForm(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    email: str
    firstname: str
    lastname: str
    is_superuser: bool = Field(default=False)
    is_active: bool = Field(default=True)


class UserResponseIn(UserCreate, PasswordMixin):
    password: str
    password_repeat: str

    @field_validator('password', mode='after')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return PasswordMixin.validate_password(v)

    @field_validator('password_repeat', mode='after')
    @classmethod
    def validate_password_repeat(cls, v: str, info: ValidationInfo) -> str:
        return PasswordMixin.validate_password_repeat(v, info)


class UserUpdate(UserCreate):
    id: int
    change_password: Optional[bool] = False
    password: Optional[str] = None
    password_repeat: Optional[str] = None

    @field_validator('password', mode='after')
    @classmethod
    def validate_password(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        return PasswordMixin.validate_password_optional(v, info)

    @field_validator('password_repeat', mode='after')
    @classmethod
    def validate_password_repeat(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        return PasswordMixin.validate_password_repeat_optional(v, info)


class UserResponseInDb(UserResponseOut):
    password: str
