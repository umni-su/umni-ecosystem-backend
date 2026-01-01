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

from sqlmodel import select, delete, col, update
from typing import Set, List, Optional
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.user import UserEntity
from entities.permission import (
    PermissionEntity,
    UserRoleEntity,
    RolePermissionEntity,
    RoleEntity
)
from models.permission_model import (
    RoleModelWithPermissions,
    RoleCreate,
    RoleUpdate,
    RoleModel,
    PermissionCreate,
    PermissionModel
)


class PermissionManager:
    """Простой менеджер прав без групп"""

    def get_user_permissions(self, user_id: int) -> Set[str]:
        """
        Получить ВСЕ разрешения пользователя.
        Возвращает set с кодами разрешений.
        """
        with write_session() as session:
            try:
                # 1. Проверяем, супер-админ ли пользователь
                user = session.exec(
                    select(UserEntity).where(UserEntity.id == user_id)
                ).first()

                if not user:
                    return set()

                # Если пользователь супер-админ - возвращаем все разрешения
                if user.is_superuser:
                    all_permissions = session.exec(
                        select(PermissionEntity.code)
                    ).all()
                    return set(all_permissions)

                # 2. Обычный пользователь - собираем разрешения из ролей
                permissions = set()

                # Находим все роли пользователя
                user_roles = session.exec(
                    select(UserRoleEntity).where(UserRoleEntity.user_id == user_id)
                ).all()

                for user_role in user_roles:
                    role = user_role.role

                    # Добавляем все разрешения роли
                    for role_perm in role.role_permissions:
                        permissions.add(role_perm.permission.code)

                return permissions
            except Exception as e:
                Logger.err(str(e), LoggerType.USERS)
                return set()

    def has_permission(self, user_id: int, permission_code: str) -> bool:
        """Проверить, есть ли у пользователя конкретное разрешение"""
        permissions = self.get_user_permissions(user_id)
        return permission_code in permissions

    def has_any_permission(self, user_id: int, permission_codes: List[str]) -> bool:
        """Проверить, есть ли хотя бы одно из разрешений"""
        permissions = self.get_user_permissions(user_id)
        return any(code in permissions for code in permission_codes)

    def assign_role_to_user(self, user_id: int, role_id: int) -> bool:
        """Назначить роль пользователю"""
        with write_session() as session:
            try:
                # Проверяем, не назначена ли уже эта роль
                existing = session.exec(
                    select(UserRoleEntity).where(
                        UserRoleEntity.user_id == user_id,
                        UserRoleEntity.role_id == role_id
                    )
                ).first()

                if existing:
                    return False  # Роль уже назначена

                user_role = UserRoleEntity(
                    user_id=user_id,
                    role_id=role_id
                )
                session.add(user_role)
                session.commit()
                return True
            except Exception as e:
                Logger.err(str(e), LoggerType.USERS)
                return False

    def remove_role_from_user(self, user_id: int, role_id: int) -> bool:
        """Удалить роль у пользователя"""
        with write_session() as session:
            try:
                user_role = session.exec(
                    select(UserRoleEntity).where(
                        UserRoleEntity.user_id == user_id,
                        UserRoleEntity.role_id == role_id
                    )
                ).first()

                if user_role:
                    session.delete(user_role)
                    session.commit()
                    return True
            except Exception as e:
                Logger.err(str(e), LoggerType.USERS)
        return False

    def get_user_roles(self, user_id: int) -> List[RoleModelWithPermissions]:
        """Получить все роли пользователя"""
        with write_session() as session:
            try:
                user_roles: List[UserRoleEntity] = session.exec(
                    select(UserRoleEntity).where(UserRoleEntity.user_id == user_id)
                ).all()

                return [
                    RoleModelWithPermissions.model_validate(
                        ur.role.to_dict(
                            include_relationships=True
                        )
                    ) for ur in user_roles
                ]
            except Exception as e:
                Logger.err(str(e), LoggerType.USERS)

    def add_permission_to_role(self, role_id: int, permission_code: str) -> bool:
        """Добавить разрешение в роль"""
        with write_session() as session:
            try:
                # Находим разрешение по коду
                permission = session.exec(
                    select(PermissionEntity).where(PermissionEntity.code == permission_code)
                ).first()

                if not permission:
                    Logger.err(f"Permission not found: {permission_code}", LoggerType.USERS)
                    return False

                # Проверяем, не добавлено ли уже
                existing = session.exec(
                    select(RolePermissionEntity).where(
                        RolePermissionEntity.role_id == role_id,
                        RolePermissionEntity.permission_id == permission.id
                    )
                ).first()

                if existing:
                    return False

                role_perm = RolePermissionEntity(
                    role_id=role_id,
                    permission_id=permission.id
                )
                session.add(role_perm)
                session.commit()
                return True
            except Exception as e:
                Logger.err(str(e), LoggerType.USERS)
                return False

    def remove_permission_from_role(self, permission_id: int) -> bool:
        with write_session() as session:
            try:
                session.exec(
                    delete(RolePermissionEntity).where(
                        col(RolePermissionEntity.permission_id) == permission_id,
                    )
                )
                return True
            except Exception as e:
                Logger.err(str(e), LoggerType.USERS)
                return False

    def get_users_with_permission(self, permission_code: str) -> List[UserEntity]:
        """Получить всех пользователей, у которых есть разрешение"""
        with write_session() as session:
            try:
                # Находим разрешение
                permission: PermissionEntity | None = session.exec(
                    select(PermissionEntity).where(PermissionEntity.code == permission_code)
                ).first()

                if not permission:
                    return []

                # Находим всех пользователей через роли
                users: set = set()

                # Сначала супер-админы (они имеют все разрешения)
                superusers = session.exec(
                    select(UserEntity).where(UserEntity.is_superuser == True)
                ).all()
                users.update(superusers)

                # Затем пользователи, у которых есть роль с этим разрешением
                for role_perm in permission.role_permissions:
                    role = RoleModelWithPermissions.model_validate(role_perm.role)
                    for user_role in role.user_roles:
                        users.add(user_role.user)

                return list(users)
            except Exception as e:
                Logger.err(str(e), LoggerType.USERS)
                return []

    # === ROLES MANAGEMENT ===

    def create_role(self, role_data: RoleCreate) -> Optional[RoleEntity]:
        """Создать новую роль"""
        with write_session() as session:
            try:
                # Проверяем уникальность кода
                existing = session.exec(
                    select(RoleEntity).where(RoleEntity.code == role_data.code)
                ).first()

                if existing:
                    Logger.err(f"Role with code {role_data.code} already exists", LoggerType.USERS)
                    return None

                # Создаем роль
                role = RoleEntity(
                    code=role_data.code,
                    name=role_data.name,
                    description=role_data.description,
                    is_default=role_data.is_default,
                    is_system=False
                )

                session.add(role)
                session.commit()
                session.refresh(role)

                # Добавляем разрешения если указаны
                if role_data.permission_codes:
                    for perm_code in role_data.permission_codes:
                        self.add_permission_to_role(role.id, perm_code)

                Logger.info(f"Role created: {role_data.code}", LoggerType.USERS)
                return role

            except Exception as e:
                Logger.err(f"Error creating role: {str(e)}", LoggerType.USERS)
                session.rollback()
                return None

    def update_role(self, role_data: RoleUpdate) -> Optional[RoleEntity]:
        """Обновить существующую роль"""
        with write_session() as session:
            try:
                role = session.get(RoleEntity, role_data.id)
                if not role:
                    Logger.err(f"Role not found: {role_data.id}", LoggerType.USERS)
                    return None

                if role.is_system:
                    Logger.err(f"Cannot update system role: {role.code}", LoggerType.USERS)
                    return None

                if role_data.name is not None:
                    role.name = role_data.name
                if role_data.description is not None:
                    role.description = role_data.description
                if role_data.is_default is not None:
                    role.is_default = role_data.is_default

                session.add(role)
                session.commit()
                session.refresh(role)

                # Обновляем разрешения если указаны
                if role_data.permission_codes is not None:
                    # Удаляем все существующие разрешения
                    session.exec(
                        delete(RolePermissionEntity).where(
                            col(RolePermissionEntity.role_id) == role_data.id
                        )
                    )

                    # Добавляем новые разрешения
                    for perm_code in role_data.permission_codes:
                        self.add_permission_to_role(role_data.id, perm_code)

                Logger.info(f"Role updated: {role.code}", LoggerType.USERS)
                return role

            except Exception as e:
                Logger.err(f"Error updating role: {str(e)}", LoggerType.USERS)
                session.rollback()
                return None

    def delete_role(self, role_id: int) -> bool:
        """Удалить роль"""
        with write_session() as session:
            try:
                role = session.get(RoleEntity, role_id)
                if not role:
                    Logger.err(f"Role not found: {role_id}", LoggerType.USERS)
                    return False

                if role.is_system:
                    Logger.err(f"Cannot delete system role: {role.code}", LoggerType.USERS)
                    return False

                user_roles_count = session.exec(
                    select(UserRoleEntity).where(UserRoleEntity.role_id == role_id)
                ).all()

                if user_roles_count:
                    Logger.err(f"Cannot delete role {role.code} - it has {len(user_roles_count)} assigned users",
                               LoggerType.USERS)
                    return False

                session.exec(
                    delete(RolePermissionEntity).where(
                        col(RolePermissionEntity.role_id) == role_id
                    )
                )

                # Удаляем саму роль
                session.delete(role)
                session.commit()

                Logger.info(f"Role deleted: {role.code}", LoggerType.USERS)
                return True

            except Exception as e:
                Logger.err(f"Error deleting role: {str(e)}", LoggerType.USERS)
                session.rollback()
                return False

    def get_role_by_code(self, role_code: str) -> Optional[RoleEntity]:
        """Получить роль по коду"""
        with write_session() as session:
            try:
                role = session.exec(
                    select(RoleEntity).where(RoleEntity.code == role_code)
                ).first()
                return role
            except Exception as e:
                Logger.err(f"Error getting role: {str(e)}", LoggerType.USERS)
                return None

    def get_role_by_id(self, role_id: int) -> Optional[RoleEntity]:
        """Получить роль по ID"""
        with write_session() as session:
            try:
                role = session.get(RoleEntity, role_id)
                return role
            except Exception as e:
                Logger.err(f"Error getting role: {str(e)}", LoggerType.USERS)
                return None

    def get_all_roles(self) -> List[RoleModel]:
        """Получить все роли с разрешениями"""
        with write_session() as session:
            try:
                roles = session.exec(
                    select(RoleEntity).order_by(RoleEntity.code)
                ).all()

                return [
                    RoleModel.model_validate(
                        r.to_dict(
                            include_relationships=True
                        )
                    ) for r in roles
                ]
            except Exception as e:
                Logger.err(f"Error getting all roles: {str(e)}", LoggerType.USERS)
                return []

    def assign_role_to_user_by_code(self, user_id: int, role_code: str) -> bool:
        """Назначить роль пользователю по коду роли"""
        with write_session() as session:
            try:
                role = session.exec(
                    select(RoleEntity).where(RoleEntity.code == role_code)
                ).first()

                if not role:
                    Logger.err(f"Role not found: {role_code}", LoggerType.USERS)
                    return False

                return self.assign_role_to_user(user_id, role.id)

            except Exception as e:
                Logger.err(f"Error assigning role by code: {str(e)}", LoggerType.USERS)
                return False

    def remove_role_from_user_by_code(self, user_id: int, role_code: str) -> bool:
        """Удалить роль у пользователя по коду роли"""
        with write_session() as session:
            try:
                role = session.exec(
                    select(RoleEntity).where(RoleEntity.code == role_code)
                ).first()

                if not role:
                    Logger.err(f"Role not found: {role_code}", LoggerType.USERS)
                    return False

                return self.remove_role_from_user(user_id, role.id)

            except Exception as e:
                Logger.err(f"Error removing role by code: {str(e)}", LoggerType.USERS)
                return False

    # === PERMISSIONS MANAGEMENT ===

    def create_permission(self, perm: PermissionCreate) -> Optional[PermissionEntity]:
        """Создать новое разрешение"""
        with write_session() as session:
            try:
                # Проверяем уникальность
                existing = session.exec(
                    select(PermissionEntity).where(PermissionEntity.code == perm.code)
                ).first()

                if existing:
                    Logger.err(f"Permission already exists: {perm.code}", LoggerType.USERS)
                    return None

                permission = PermissionEntity.model_validate(perm.model_dump())

                session.add(permission)
                session.commit()
                session.refresh(permission)

                Logger.info(f"Permission created: {perm.code}", LoggerType.USERS)
                return permission

            except Exception as e:
                Logger.err(f"Error creating permission: {str(e)}", LoggerType.USERS)
                session.rollback()
                return None

    def update_permission(self, perm: PermissionModel) -> bool:
        with write_session() as session:
            try:
                permission = session.get(PermissionEntity, perm.id)
                if permission:
                    permission.code = perm.code
                    permission.name = perm.name
                    permission.description = perm.description
                    permission.category = perm.category
                    session.add(permission)
                    return True

            except Exception as e:
                Logger.err(f"Error updating permission: {str(e)}", LoggerType.USERS)
                return False
        return False

    def delete_permission(self, permission_id: int) -> bool:
        with write_session() as session:
            try:
                self.remove_permission_from_role(permission_id)
                session.exec(
                    delete(PermissionEntity).where(
                        col(PermissionEntity.id) == permission_id
                    )
                )
                return True
            except Exception as e:
                Logger.err(f"Error deleting permission: {str(e)}", LoggerType.USERS)
                return False

    def get_all_permissions(self) -> List[PermissionModel]:
        """Получить все разрешения"""
        with write_session() as session:
            try:
                permissions = session.exec(
                    select(PermissionEntity).order_by(PermissionEntity.category, PermissionEntity.code)
                ).all()

                return [
                    PermissionModel.model_validate(
                        p.to_dict(
                            include_relationships=True
                        )
                    )
                    for p in permissions
                ]
            except Exception as e:
                Logger.err(f"Error getting permissions: {str(e)}")
                return []

    def get_permissions_by_category(self, category: str) -> List[PermissionModel]:
        """Получить разрешения по категории"""
        with write_session() as session:
            try:
                permissions = session.exec(
                    select(PermissionEntity)
                    .where(PermissionEntity.category == category)
                    .order_by(PermissionEntity.code)
                ).all()

                return [
                    PermissionModel.model_validate(
                        p.to_dict(
                            include_relationships=True
                        )
                    )
                    for p in permissions
                ]
            except Exception as e:
                Logger.err(f"Error getting permissions by category: {str(e)}", LoggerType.USERS)
                return []


permission_manager = PermissionManager()
