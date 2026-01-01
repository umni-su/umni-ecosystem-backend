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

from classes.permissions.permission_manager import permission_manager
from database.session import write_session
from entities.permission import RoleEntity
from models.pagination_model import PageParams
from models.permission_model import RoleModelWithPermissions, RoleModel, RoleCreate, RoleUpdate
from repositories.base_repository import BaseRepository
from sqlmodel import delete, col


class RoleRepository(BaseRepository):
    entity_class = RoleEntity
    model_class = RoleModelWithPermissions

    @classmethod
    def get_roles(cls, params: PageParams):
        with write_session() as session:
            return cls.paginate(
                session=session,
                page_params=params,
            )

    @classmethod
    def get_role(cls, role_id: int) -> RoleModelWithPermissions | None:
        with write_session() as session:
            role = session.get(RoleEntity, role_id)
            if isinstance(role, RoleEntity):
                return RoleModelWithPermissions.model_validate(
                    role.to_dict(
                        include_relationships=True
                    )
                )

        return None

    @classmethod
    def add_role(cls, role: RoleCreate) -> Optional[RoleModelWithPermissions]:
        role_db = permission_manager.create_role(role)
        if isinstance(role_db, RoleEntity):
            return RoleModelWithPermissions.model_validate(role_db.to_dict(
                include_relationships=True
            ))

    @classmethod
    def update_role(cls, role: RoleUpdate) -> Optional[RoleModelWithPermissions]:
        role_db = permission_manager.update_role(
            role_data=role
        )
        if isinstance(role_db, RoleEntity):
            return RoleModelWithPermissions.model_validate(role_db.to_dict(
                include_relationships=True
            ))

    @classmethod
    def delete_role(cls, role_id: int) -> bool:
        return permission_manager.delete_role(role_id=role_id)
