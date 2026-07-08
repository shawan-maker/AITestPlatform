"""测试管理模块 - picker/schemas

请求/响应 Schema 定义
"""
from pydantic import BaseModel, Field

from service.core.enums import CaseCategory, ExecStatus, TaskSuiteType
from service.core.pagination import Paginated, PaginationParams


class ApiCasePickerOut(BaseModel):
    """API用例选择器out"""
    id: int
    title: str
    interface_id: int
    interface_name: str | None = None
    interface_path: str | None = None
    interface_method: str | None = None
    exec_status: ExecStatus


class PaginatedApiCasePicker(Paginated[ApiCasePickerOut]):
    """paginatedAPI用例选择器"""
    pass


class FunctionalCasePickerOut(BaseModel):
    """functional用例选择器out"""
    id: int
    case_name: str
    case_no: str | None = None
    module_id: int | None
    module_name: str | None = None
    catalog_id: int | None
    priority: int | None = None
    case_category: CaseCategory | None = None


class PaginatedFunctionalCasePicker(Paginated[FunctionalCasePickerOut]):
    """paginatedfunctional用例选择器"""
    pass


class SuitePickerOut(BaseModel):
    """套件选择器out"""
    id: int
    suite_name: str
    type: TaskSuiteType
    case_count: int = 0


class PaginatedSuitePicker(Paginated[SuitePickerOut]):
    """paginated套件选择器"""
    pass


class ApiCasePickerQuery(PaginationParams):
    """API用例选择器query"""
    project_id: int = Field(ge=1)
    q: str | None = None


class FunctionalCasePickerQuery(PaginationParams):
    """functional用例选择器query"""
    project_id: int = Field(ge=1)
    q: str | None = None
    module_id: int | None = None


class SuitePickerQuery(PaginationParams):
    """套件选择器query"""
    project_id: int = Field(ge=1)
    type: TaskSuiteType | None = None
    q: str | None = None
