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
from classes.permissions.permission_decorators import register_permission, register_permission_category, \
    register_category_permissions
from classes.permissions.permission_dependency import check_permission
from models.pagination_model import PageParams
from models.permission_model import PermissionModel
from repositories.permission_repository import PermissionRepository
from responses.user import UserResponseOut

tag = "permissions"

permissions = APIRouter(
    prefix='/permissions',
    tags=['permissions']
)

register_category_permissions(
    category_code="permissions",
    category_name=_('Permissions management'),
    permissions=[
        {
            "code": "permissions:view",
            "name": _("View permissions"),
            "description": _("Allow to view permissions")
        },
        {
            "code": "permissions:delete",
            "name": _("Delete permissions"),
            "description": _("Allow to delete permissions")
        }
    ]
)


@permissions.post('/list')
def get_permissions(
        params: PageParams,
        user: Annotated[UserResponseOut, Depends(check_permission("permissions:view"))]
):
    try:
        return PermissionRepository.get_permissions_grouped()
    except Exception as e:
        from fastapi import HTTPException
        return HTTPException(status_code=500, detail=str(e))
