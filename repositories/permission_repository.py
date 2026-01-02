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
from typing import Optional, List

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.permissions.permission_decorators import get_permission_categories
from database.session import write_session
from entities.permission import PermissionEntity
from entities.user import UserEntity
from models.pagination_model import PageParams
from models.permission_model import PermissionModel, PermissionGroupModel
from repositories.base_repository import BaseRepository
from responses.user import UserResponseOut, UserResponseIn, UserUpdate
from sqlmodel import delete, col, select


class PermissionRepository(BaseRepository):
    entity_class = PermissionEntity
    model_class = PermissionModel

    @classmethod
    def get_permissions(cls, params: PageParams):
        with write_session() as session:
            return cls.paginate(
                session=session,
                page_params=params,
            )

    @classmethod
    def get_all_permissions(cls):
        with write_session() as session:
            try:
                permissions = session.exec(
                    select(PermissionEntity).order_by(
                        col(PermissionEntity.category).asc()
                    ).order_by(
                        col(PermissionEntity.name).asc()
                    )
                )
                return [
                    PermissionModel.model_validate(
                        p.to_dict()
                    ) for p in permissions
                ]
            except Exception as e:
                Logger.err(str(e))
                return None

    @classmethod
    def get_permissions_grouped(cls) -> List[PermissionGroupModel]:
        permissions = cls.get_all_permissions()
        groups = get_permission_categories()
        res: List[PermissionGroupModel] = []
        for code, name in groups.items():
            group = PermissionGroupModel(
                name=name,
                code=code,
                permissions=[p for p in permissions if p.category == code],
            )
            res.append(group)
        return res

    @classmethod
    def get_permission_by_id(cls, permission_id: int) -> Optional[PermissionModel]:
        with write_session() as session:
            try:
                return PermissionModel.model_validate(
                    session.get(PermissionEntity, permission_id).to_dict(
                        include_relationships=True
                    )
                )

            except Exception as e:
                Logger.err(str(e))
                return None
