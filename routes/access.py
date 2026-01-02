# Copyright (C) 2026 Mikhail Sazanov
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

from typing import Optional, Annotated

from fastapi import APIRouter, HTTPException, Depends

from classes.l10n.l10n import _
from classes.permissions.permission_decorators import register_permission, register_permission_category, \
    register_category_permissions
from classes.permissions.permission_dependency import check_permission
from classes.permissions.permission_manager import permission_manager
from models.pagination_model import PageParams
from models.permission_model import RoleModelWithPermissions, RoleCreate, RoleUpdate
from repositories.permission_repository import PermissionRepository
from repositories.role_repository import RoleRepository
from responses.user import UserResponseOut

access = APIRouter(
    prefix='/access',
    tags=['access']
)


register_category_permissions(
    category_code="roles",
    category_name=_('Roles management'),
    permissions=[
        {
            "code": "roles:view",
            "name": _("View roles"),
            "description": _("Allow to view roles list")
        },
        {
            "code": "roles:create",
            "name": _("Create roles"),
            "description": _("Allow to create roles")
        },
        {
            "code": "roles:update",
            "name": _("Update roles"),
            "description": _("Allow to update roles")
        },
        {
            "code": "role:permissions:create",
            "name": _("Assign permissions to role"),
            "description": _("Allow to assign permissions to role")
        },
        {
            "code": "role:permissions:remove",
            "name": _("Remove permissions from role"),
            "description": _("Allow to remove permissions from role")
        }
    ]
)


@access.post('/roles/list')
def get_roles(
        params: PageParams,
        user: Annotated[UserResponseOut, Depends(check_permission("roles:view"))]
):
    try:
        return RoleRepository.get_roles(
            params=params
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@access.get('/roles/{role_id}')
def get_role(
        role_id: int,
        user: Annotated[UserResponseOut, Depends(check_permission("roles:view"))]
) -> Optional[RoleModelWithPermissions]:
    try:
        return RoleRepository.get_role(
            role_id=role_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@access.post('/roles')
def create_role(
        model: RoleCreate,
        user: Annotated[UserResponseOut, Depends(check_permission("roles:create"))]
) -> Optional[RoleModelWithPermissions]:
    try:
        return RoleRepository.add_role(
            role=model
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@access.put('/roles/{role_id}')
def update_role(
        role_id: int,
        model: RoleUpdate,
        user: Annotated[UserResponseOut, Depends(check_permission("roles:update"))]
) -> Optional[RoleModelWithPermissions]:
    try:
        return RoleRepository.update_role(
            role=model
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@access.put('/roles/{role_id}')
def delete_role(
        role_id: int,
        user: Annotated[UserResponseOut, Depends(check_permission("roles:delete"))]
):
    try:
        status = RoleRepository.delete_role(
            role_id=role_id
        )
        raise HTTPException(
            status_code=200 if status else 500
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@access.put('/roles/{role_id}/permissions/{permission_id}')
def add_permissions_to_role(
    role_id: int,
    permission_id: int,
    user: Annotated[UserResponseOut, Depends(check_permission("role:permissions:create"))]
):
    permission = PermissionRepository.get_permission_by_id(permission_id=permission_id)
    res = permission_manager.add_permission_to_role(
        role_id=role_id,
        permission_code=permission.code
    )
    return HTTPException(
        status_code=200 if res else 500,
    )

@access.delete('/roles/{role_id}/permissions/{permission_id}')
def add_permissions_to_role(
    role_id: int,
    permission_id: int,
    user: Annotated[UserResponseOut, Depends(check_permission("role:permissions:remove"))]
):
    res = permission_manager.remove_permission_from_role(
        role_id=role_id,
        permission_id=permission_id
    )
    return HTTPException(
        status_code=200 if res else 500,
    )