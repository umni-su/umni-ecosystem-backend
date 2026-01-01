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

from functools import wraps
from typing import Optional

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.permission import PermissionEntity
from sqlmodel import select

_created_permissions = set()


def register_permission(
        code: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None
):
    def decorator(func):
        if not name:
            # "video:camera:view" -> "Video Camera View"
            generated_name = code.replace(":", " ").title()
        else:
            generated_name = name

        if not category:
            if ":" in code:
                generated_category = code.split(":")[0]  # video:camera:view -> video
            else:
                generated_category = "system"
        else:
            generated_category = category

        if not description:
            generated_description = f"Разрешение: {generated_name}"
        else:
            generated_description = description

        _create_permission(
            code=code,
            name=generated_name,
            description=generated_description,
            category=generated_category
        )

        func.permission_code = code
        func.permission_name = generated_name

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _create_permission(code: str, name: str, description: str, category: str):
    """Создать разрешение в БД если его еще нет"""
    if code in _created_permissions:
        return

    with write_session() as session:
        try:
            existing = session.exec(
                select(PermissionEntity).where(PermissionEntity.code == code)
            ).first()

            if existing:
                existing.name = name
                existing.description = description
                existing.category = category
                session.add(existing)
                session.commit()
                _created_permissions.add(code)
                Logger.debug(f"✅ Permission updated: {code} ({name})", LoggerType.USERS)
                return

            # Создаем новое разрешение
            permission = PermissionEntity(
                code=code,
                name=name,
                description=description,
                category=category
            )

            session.add(permission)
            session.commit()

            # Добавляем в кэш
            _created_permissions.add(code)

            Logger.debug(f"✅ Permission created: {code} ({name})", LoggerType.USERS)

        except Exception as e:
            Logger.err(f"❌ Error creating permission {code}: {e}", LoggerType.USERS)
            session.rollback()


# Вспомогательная функция для массового создания
def ensure_permissions(permissions_list: list):
    """
    ensure_permissions([
        {"code": "video:camera:view", "name": "Просмотр камер"},
        {"code": "video:camera:create", "name": "Создание камер"},
    ])
    """
    for perm in permissions_list:
        _create_permission(
            code=perm["code"],
            name=perm.get("name", ""),
            description=perm.get("description", ""),
            category=perm.get("category", "")
        )
