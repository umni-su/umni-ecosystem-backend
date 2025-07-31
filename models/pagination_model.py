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
