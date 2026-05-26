from typing import Literal

from pydantic import BaseModel, Field


class ImportInterfacesRequest(BaseModel):
    module_id: int = Field(..., ge=1)
    import_mode: Literal["skip", "upsert"] = "skip"


class ImportInterfacesResult(BaseModel):
    created: int
    updated: int
    skipped: int
    interface_ids: list[int]
