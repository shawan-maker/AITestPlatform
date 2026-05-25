from enum import Enum


class ConfigType(str, Enum):
    scalar = "scalar"
    json = "json"
    secret = "secret"


class RagType(str, Enum):
    requirement = "requirement"
    api = "api"


class KnowledgeDocType(str, Enum):
    requirement = "requirement"
    api_doc = "api_doc"
    other = "other"


class IndexStatus(str, Enum):
    pending = "pending"
    indexing = "indexing"
    indexed = "indexed"
    failed = "failed"
    na = "na"


class RequirementStatus(str, Enum):
    draft = "draft"
    reviewing = "reviewing"
    approved = "approved"
    rejected = "rejected"
    changed = "changed"


class SourceType(str, Enum):
    manual = "manual"
    ai = "ai"


class FunctionalCaseType(str, Enum):
    functional = "functional"
    ui = "ui"


class FunctionalCaseStatus(str, Enum):
    design = "design"
    ready = "ready"
    smoke = "smoke"
    regression = "regression"
    obsolete = "obsolete"


class ContentFormat(str, Enum):
    text = "text"
    json = "json"


class ApiInterfaceSource(str, Enum):
    swagger = "swagger"
    openapi = "openapi"
    rag = "rag"
    manual = "manual"


class ApiBaseCaseStatus(str, Enum):
    draft = "draft"
    approved = "approved"
    archived = "archived"


class ApiTestCaseType(str, Enum):
    api = "api"
    business = "business"


class ReviewStatus(str, Enum):
    init = "init"
    success = "success"
    fail = "fail"
    error = "error"


class ExecStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    disabled = "disabled"


class TaskSuiteType(str, Enum):
    api = "api"
    functional = "functional"
    ui = "ui"


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class SuiteCaseType(str, Enum):
    api = "api"
    functional = "functional"


class CaseRunStatus(str, Enum):
    success = "success"
    fail = "fail"
    error = "error"


class GenType(str, Enum):
    functional = "functional"
    api_base = "api_base"
    api_runnable = "api_runnable"


class InputRefType(str, Enum):
    requirement = "requirement"
    interface = "interface"
    api_doc = "api_doc"


class SessionStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class ProjectMemberRole(int, Enum):
    def __new__(cls, value: int, label: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj

    viewer = (0, "项目查看者")
    editor = (1, "项目编辑者")
    owner = (2, "项目所有者")


def project_member_role_label(role: int) -> str:
    try:
        return ProjectMemberRole(role).label
    except ValueError:
        return "未知角色"
