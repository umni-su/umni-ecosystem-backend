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

from datetime import datetime
from enum import StrEnum
from typing import Generic, TypeVar, List, Any
from pydantic import BaseModel

T = TypeVar('T')


class PageParams(BaseModel):
    page: int = 1
    size: int = 10


class EventsPageType(StrEnum):
    STREAM = 'stream',
    EVENTS = 'events',
    ALERTS = 'alerts',


class TimelineParams(BaseModel):
    start: datetime
    end: datetime


class EventResultDirection(StrEnum):
    START = 'start',
    END = 'end',


class EventsPageParams(PageParams):
    type: None | EventsPageType = None
    event_id: int | None = None
    direction: EventResultDirection | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    async def paginate(
            cls,
            query: Any,
            page: int = 1,
            size: int = 10,
    ):
        pass
