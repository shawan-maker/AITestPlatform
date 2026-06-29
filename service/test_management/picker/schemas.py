from pydantic import BaseModel, Field

from service.core.enums import CaseCategory, ExecStatus, TaskSuiteType
from service.core.pagination import Paginated, PaginationParams


class ApiCasePickerOut(BaseModel):
    id: int
    title: str
    interface_id: int
    interface_name: str | None = None
    interface_path: str | None = None
    interface_method: str | None = None
    exec_status: ExecStatus


class PaginatedApiCasePicker(Paginated[ApiCasePickerOut]):
    pass


class FunctionalCasePickerOut(BaseModel):
    id: int
    case_name: str
    case_no: str | None = None
    module_id: int | None
    module_name: str | None = None
    catalog_id: int | None
    priority: int | None = None
    case_category: CaseCategory | None = None


class PaginatedFunctionalCasePicker(Paginated[FunctionalCasePickerOut]):
    pass


class SuitePickerOut(BaseModel):
    id: int
    suite_name: str
    type: TaskSuiteType
    case_count: int = 0


class PaginatedSuitePicker(Paginated[SuitePickerOut]):
    pass


class ApiCasePickerQuery(PaginationParams):
    project_id: int = Field(ge=1)
    q: str | None = None


class FunctionalCasePickerQuery(PaginationParams):
    project_id: int = Field(ge=1)
    q: str | None = None
    module_id: int | None = None


class SuitePickerQuery(PaginationParams):
    project_id: int = Field(ge=1)
    type: TaskSuiteType | None = None
    q: str | None = None
