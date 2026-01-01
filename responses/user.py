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


class UserResponseIn(UserCreate, PasswordMixin):
    password: str
    password_repeat: str

    _validate_password = field_validator('password')(PasswordMixin.validate_password)
    _validate_password_repeat = field_validator('password_repeat')(PasswordMixin.validate_password_repeat)


class UserUpdate(UserCreate):
    id: int
    change_password: Optional[bool] = False
    password: Optional[str] = None
    password_repeat: Optional[str] = None

    _validate_password = field_validator('password')(PasswordMixin.validate_password_optional)
    _validate_password_repeat = field_validator('password_repeat')(PasswordMixin.validate_password_repeat_optional)


class UserResponseInDb(UserResponseOut):
    password: str
