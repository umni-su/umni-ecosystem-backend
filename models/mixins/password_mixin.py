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
from typing import Optional
from pydantic import ValidationInfo
import re

from classes.l10n.l10n import _


class PasswordMixin:
    """Миксин с валидацией пароля"""

    @staticmethod
    def validate_password_strength(v: str) -> str:
        """Общая функция валидации сложности пароля"""
        if len(v) < 8:
            raise ValueError(_('Password must be at least 8 characters long'))

        pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()_+=\-~])[A-Za-z\d!@#$%^&*()_+=\-~]+$'

        if not re.match(pattern, v):
            raise ValueError(
                _('Password must contain: uppercase letter, lowercase letter, digit, and special character (!@#$%^&*()_+=-~)')
            )
        return v

    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидатор для обязательного пароля"""
        return cls.validate_password_strength(v)

    @classmethod
    def validate_password_repeat(cls, v: str, info: ValidationInfo) -> str:
        """Валидатор для подтверждения пароля"""
        if 'password' in info.data and v != info.data['password']:
            raise ValueError(_('Passwords do not match'))
        return v

    @classmethod
    def validate_password_optional(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Валидатор для опционального пароля (только при change_password=True)"""
        if info.data.get('change_password') and v is not None:
            return cls.validate_password_strength(v)
        return v

    @classmethod
    def validate_password_repeat_optional(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Валидатор для опционального подтверждения пароля"""
        if info.data.get('change_password'):
            password = info.data.get('password')

            if v is not None and password is None:
                raise ValueError(_('Password is required when changing password'))

            if v is not None and password is not None and v != password:
                raise ValueError(_('Passwords do not match'))
        return v
