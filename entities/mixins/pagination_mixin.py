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

from typing import TypeVar, List, Any
from sqlmodel import select, func, SQLModel

from models.pagination_model import PaginatedResponse

T = TypeVar('T', bound=SQLModel)


class PaginationMixin:
    """Миксин для добавления пагинации к моделям SQLModel"""

    @classmethod
    def paginate(
            cls,
            session,
            page: int = 1,
            size: int = 10,
            where_conditions: List[Any] = None,
            order_by: Any = None,
            include_relationships: bool = False
    ) -> "PaginatedResponse[dict]":
        """
        Пагинирует результаты запроса

        Args:
            session: Сессия базы данных
            page: Номер страницы
            size: Размер страницы
            where_conditions: Список условий WHERE
            order_by: Поле для сортировки
            include_relationships: Включать ли связанные объекты
        """
        # Базовый запрос для данных
        query = select(cls)

        # Базовый запрос для подсчета
        count_query = select(func.count(cls.id))

        # Применяем условия WHERE если есть
        if where_conditions:
            for condition in where_conditions:
                query = query.where(condition)
                count_query = count_query.where(condition)

        # Применяем сортировку если указана
        if order_by is not None:
            query = query.order_by(order_by)

        # Получаем общее количество
        total = session.exec(count_query).first() or 0

        # Применяем пагинацию
        query = query.offset((page - 1) * size).limit(size)

        # Выполняем запрос и преобразуем в словари
        items = session.exec(query).all()
        dict_items = [item.to_dict(include_relationships=include_relationships) for item in items]

        return PaginatedResponse[dict].create(
            items=dict_items,
            total=total,
            page=page,
            size=size
        )

    @classmethod
    def paginate_to_model(
            cls,
            session,
            model_class: Any,
            page: int = 1,
            size: int = 10,
            where_conditions: List[Any] = None,
            order_by: Any = None,
            include_relationships: bool = False
    ) -> "PaginatedResponse[Any]":
        """
        Пагинирует и преобразует в Pydantic модель
        """
        dict_response = cls.paginate(
            session=session,
            page=page,
            size=size,
            where_conditions=where_conditions,
            order_by=order_by,
            include_relationships=include_relationships
        )
        # Преобразуем словари в модели
        model_items = [model_class.model_validate(item) for item in dict_response.items]

        return PaginatedResponse[model_class].create(
            items=model_items,
            total=dict_response.total,
            page=dict_response.page,
            size=dict_response.size
        )
