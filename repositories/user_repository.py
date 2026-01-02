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

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.user import UserEntity
from models.pagination_model import PageParams
from repositories.base_repository import BaseRepository
from responses.user import UserResponseOut, UserResponseIn, UserUpdate
from sqlmodel import delete, col, select, func


class UserRepository(BaseRepository):
    entity_class = UserEntity
    model_class = UserResponseOut

    @classmethod
    def count_users(
            cls,
            superusers_only: bool = False
    ) -> int:
        with write_session() as session:
            try:
                query = select(func.count(UserEntity.id)).select_from(cls.entity_class)
                if superusers_only:
                    query = query.where(col(UserEntity.is_superuser) == True)
                return session.exec(query).one_or_none()

            except Exception as e:
                Logger.err(str(e), LoggerType.USERS)
                return -1

    @classmethod
    def get_users(cls, params: PageParams):
        with write_session() as session:
            return cls.paginate(
                session=session,
                page_params=params,
            )

    @classmethod
    def create_user(cls, user: UserResponseIn) -> UserResponseOut | None:
        with write_session() as session:
            try:
                user_db = UserEntity.model_validate(
                    user.model_dump()
                )

                session.add(user_db)
                session.commit()
                session.refresh(user_db)
                return UserResponseOut.model_validate(
                    user_db.to_dict(
                        include_relationships=True
                    )
                )
            except Exception as e:
                Logger.err(f'Error create user: {str(e)}', LoggerType.USERS)

    @classmethod
    def update_user(cls, user: UserUpdate) -> UserResponseOut | None:
        with write_session() as session:
            try:
                user_db = session.get(UserEntity, user.id)

                if isinstance(user_db, UserEntity):
                    user_db.email = user.email
                    user_db.username = user.username
                    user_db.firstname = user.firstname
                    user_db.lastname = user.lastname
                    if user_db.change_password:
                        session.add(user_db)
                        session.commit()
                        session.refresh(user_db)
                        return UserResponseOut.model_validate(
                            user_db.to_dict(
                                include_relationships=True
                            )
                        )
            except Exception as e:
                Logger.err(f'Error create user: {str(e)}', LoggerType.USERS)

    @classmethod
    def delete_user(cls, user_id: int) -> bool:
        with write_session() as session:
            try:
                session.exec(
                    delete(UserEntity).where(col(UserEntity.id) == user_id)
                )
                return True
            except Exception as e:
                Logger.err(f'Error create user: {str(e)}', LoggerType.USERS)
        return False
