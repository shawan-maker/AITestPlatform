from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import RunStatus


class LastRunBrief(BaseModel):
    run_id: int | None = None
    status: RunStatus | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    passed_cases: int = 0
    total_cases: int = 0
    success_rate: str | None = None


class RelationItemBase(BaseModel):
    case_id: int
    case_order: int = Field(ge=1)


class SuccessRateMixin(BaseModel):
    success_rate: str | None = None
