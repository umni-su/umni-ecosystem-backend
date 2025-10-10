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

from typing import TypeVar, List, Any, Type
from sqlmodel import SQLModel, or_
from models.pagination_model import PaginatedResponse, PageParams

T = TypeVar('T', bound=SQLModel)
M = TypeVar('M')

'''
# Простая пагинация всех камер
cameras_page = CameraRepository.get_all_paginated(session, page_params)

# Поиск сенсоров с пагинацией
sensors_page = SensorRepository.find_sensors_paginated(
    session, 
    page_params, 
    term="temperature"
)

# Конкретная камера (вернется как страница с 1 элементом)
camera_page = CameraRepository.get_by_id_paginated(session, camera_id, page_params)
'''


class BaseRepository:
    entity_class: Type[T]
    model_class: Type[M]

    @classmethod
    def get_all_paginated(
            cls,
            session,
            page_params: PageParams,
            order_by: Any = None,
            include_relationships: bool = False
    ) -> PaginatedResponse[M]:
        """Получить все записи с пагинацией"""
        return cls.paginate(
            session=session,
            page_params=page_params,
            order_by=order_by,
            include_relationships=include_relationships
        )

    @classmethod
    def get_by_id_paginated(
            cls,
            session,
            entity_id: int,
            page_params: PageParams,
            include_relationships: bool = False
    ) -> PaginatedResponse[M] | None:
        """Получить конкретную запись (вернется как список из 1 элемента)"""
        where_conditions = [cls.entity_class.id == entity_id]

        result = cls.paginate(
            session=session,
            page_params=page_params,
            where_conditions=where_conditions,
            include_relationships=include_relationships
        )

        return result if result.total > 0 else None

    @classmethod
    def find_paginated(
            cls,
            session,
            page_params: PageParams,
            search_term: str,
            search_fields: List[Any],
            include_relationships: bool = False
    ) -> PaginatedResponse[M]:
        """Универсальный поиск с пагинацией"""
        if not search_term:
            return cls.get_all_paginated(session, page_params, include_relationships=include_relationships)

        search_conditions = [field.ilike(f"%{search_term}%") for field in search_fields]
        where_conditions = [or_(*search_conditions)] if search_conditions else []

        return cls.paginate(
            session=session,
            page_params=page_params,
            where_conditions=where_conditions,
            include_relationships=include_relationships
        )

    @classmethod
    def paginate(
            cls,
            session,
            page_params: PageParams,
            where_conditions: List[Any] = None,
            order_by: Any = None,
            include_relationships: bool = False
    ) -> PaginatedResponse[M]:
        """Базовый метод пагинации для всех репозиториев"""
        return cls.entity_class.paginate_to_model(
            session=session,
            model_class=cls.model_class,
            page=page_params.page,
            size=page_params.size,
            where_conditions=where_conditions,
            order_by=order_by,
            include_relationships=include_relationships
        )
