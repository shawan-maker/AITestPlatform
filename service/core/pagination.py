from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from tortoise.queryset import QuerySet

T = TypeVar("T")

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


class Paginated(BaseModel, Generic[T]):
    """paginated"""
    total: int
    page: int
    page_size: int
    items: list[T]


class PaginationParams(BaseModel):
    """paginationparams"""
    page: int = Field(DEFAULT_PAGE, ge=1)
    page_size: int = Field(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)


async def paginate(qs: QuerySet, page: int, page_size: int) -> tuple[int, list]:
    total = await qs.count()
    offset = (page - 1) * page_size
    items = await qs.offset(offset).limit(page_size)
    return total, items
