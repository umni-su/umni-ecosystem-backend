from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar('T')


class PageParams(BaseModel):
    page: int = 1
    size: int = 10


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
