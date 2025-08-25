#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Any, Dict, List, Set
from sqlalchemy.orm import class_mapper


class BaseModelMixin:
    """Миксин для универсальной сериализации SQLAlchemy объектов с отношениями"""

    def to_dict(self, include_relationships: bool = False, exclude: List[str] = None, visited: Set[int] = None) -> Dict[
        str, Any]:
        """
        Преобразует SQLAlchemy объект в словарь

        Args:
            include_relationships: Включать ли связанные объекты
            exclude: Список полей для исключения
            visited: Множество посещенных объектов (для защиты от циклических ссылок)

        Returns:
            Словарь с данными объекта
        """
        if exclude is None:
            exclude = []
        if visited is None:
            visited = set()

        # Защита от циклических ссылок
        obj_id = id(self)
        if obj_id in visited:
            return {"__cycle__": f"{self.__class__.__name__}_{obj_id}"}
        visited.add(obj_id)

        result = {}
        mapper = class_mapper(self.__class__)

        # Базовые атрибуты
        for column in mapper.columns:
            if column.key not in exclude:
                result[column.key] = getattr(self, column.key)

        # Отношения
        if include_relationships:
            for relationship in mapper.relationships:
                if relationship.key not in exclude:
                    related_obj = getattr(self, relationship.key)
                    if related_obj is not None:
                        if relationship.uselist:  # One-to-Many или Many-to-Many
                            result[relationship.key] = [
                                item.to_dict(include_relationships=False, exclude=exclude, visited=visited)
                                if hasattr(item, 'to_dict') else
                                self._simple_convert(item)
                                for item in related_obj
                            ]
                        else:  # One-to-One или Many-to-One
                            result[relationship.key] = (
                                related_obj.to_dict(include_relationships=False, exclude=exclude, visited=visited)
                                if hasattr(related_obj, 'to_dict') else
                                self._simple_convert(related_obj)
                            )

        visited.remove(obj_id)
        return result

    def _simple_convert(self, obj: Any) -> Any:
        """Простое преобразование объекта в базовые типы"""
        if hasattr(obj, '__dict__'):
            # Исключаем внутренние атрибуты
            return {k: v for k, v in obj.__dict__.items()
                    if not k.startswith('_') and k != 'metadata'}
        return obj
