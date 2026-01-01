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

from fastapi import APIRouter, Depends

from classes.l10n.l10n import _
from classes.permissions.permission_decorators import register_permission
from classes.permissions.permission_dependency import check_permission
from models.pagination_model import PageParams
from repositories.user_repository import UserRepository
from responses.user import UserResponseOut, UserResponseIn, UserUpdate

users = APIRouter(
    prefix='/users',
    tags=['users']
)


@register_permission(
    code="users:view",
    name=_("View users"),
    description=_("Allow to view users list"),
    category="users"
)
@register_permission(
    code="users:create",
    name=_("Creating users"),
    description=_("Allow to create users"),
    category="users"
)
@register_permission(
    code="users:update",
    name=_("Updating users"),
    description=_("Allow to update users"),
    category="users"
)
@register_permission(
    code="users:delete",
    name=_("Deleting users"),
    description=_("Allow to delete users"),
    category="users"
)
@users.post('/list')
def get_users(
        params: PageParams,
        user: Annotated[UserResponseOut, Depends(check_permission("users:view"))]
):
    return UserRepository.get_users(params=params)


@users.post('')
def create_user(
        model: UserResponseIn,
        user: Annotated[UserResponseOut, Depends(check_permission("users:create"))]
):
    return UserRepository.create_user(model)


@users.put('/{user_id}')
def update_user(
        user_id: int,
        model: UserUpdate,
        user: Annotated[UserResponseOut, Depends(check_permission("users:update"))]
):
    return UserRepository.update_user(model)


@users.delete('/{user_id}')
def delete_user(
        user_id: int,
        user: Annotated[UserResponseOut, Depends(check_permission("users:delete"))]
):
    return UserRepository.delete_user(user_id)
