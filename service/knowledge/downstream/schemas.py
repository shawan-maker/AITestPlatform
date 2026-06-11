from typing import Any, Literal

from pydantic import BaseModel, Field


class ImportInterfacesRequest(BaseModel):
    module_id: int | None = Field(default=None, ge=1)
    catalog_id: int | None = Field(default=None, ge=1)
    items: list[dict[str, Any]] | None = None


class ImportInterfacesResult(BaseModel):
    created: int
    updated: int
    skipped: int
    interface_ids: list[int]
