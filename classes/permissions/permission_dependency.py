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
from typing import Annotated

from fastapi import HTTPException, status, Depends

from classes.auth.auth import Auth
from classes.permissions.permission_manager import permission_manager
from responses.user import UserResponseOut


def check_permission(permission_code: str):
    """Проверка прав для пользователя"""

    async def dependency(
            user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
    ) -> UserResponseOut:
        if not permission_manager.has_permission(user.id, permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {permission_code}"
            )
        return user

    return dependency


def check_permission_by_token(permission_code: str):
    """Проверка прав для пользователя"""

    async def dependency(
            user: Annotated[UserResponseOut, Depends(Auth.validate_token)]
    ) -> UserResponseOut:
        if not permission_manager.has_permission(user.id, permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {permission_code}"
            )
        return user

    return dependency


def check_any_permission(*permission_codes: str):
    """Проверяет, есть ли хотя бы одно из прав"""

    async def dependency(
            user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
    ) -> UserResponseOut:
        for code in permission_codes:
            if permission_manager.has_permission(user.id, code):
                return user

        raise HTTPException(
            status_code=403,
            detail=f"Need any of permissions: {', '.join(permission_codes)}"
        )

    return dependency
