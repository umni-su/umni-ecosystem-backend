from typing import Generic, TypeVar, List, Any
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
