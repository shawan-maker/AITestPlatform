from enum import Enum


class ConfigType(str, Enum):
    scalar = "scalar"
    json = "json"
    secret = "secret"


class DbType(str, Enum):
    mysql = "mysql"
    sqlserver = "sqlserver"
    oracle = "oracle"


class DebugVarSource(str, Enum):
    engine = "engine"
    manual = "manual"


class RagType(str, Enum):
    api = "api"


class KnowledgeDocType(str, Enum):
    requirement = "requirement"
    api_doc = "api_doc"
    other = "other"


class IndexStatus(str, Enum):
    pending = "pending"
    indexing = "indexing"
    parsing = "parsing"
    indexed = "indexed"
    failed = "failed"
    na = "na"


class ParseMode(str, Enum):
    openapi = "openapi"
    swagger = "swagger"
    ai = "ai"


class ParseStatus(str, Enum):
    pending = "pending"
    parsing = "parsing"
    parsed = "parsed"
    failed = "failed"


class ActualParseRoute(str, Enum):
    ai_text = "ai_text"
    ai_multimodal = "ai_multimodal"
    swagger = "swagger"
    openapi = "openapi"
    auto_text = "auto_text"


class RagBackend(str, Enum):
    rag_client = "rag_client"
    rag_manager = "rag_manager"


class FunctionalExecResult(str, Enum):
    pending = "pending"
    passed = "passed"
    failed = "failed"
    blocked = "blocked"
    skipped = "skipped"


class SourceType(str, Enum):
    manual = "manual"
    ai = "ai"


class CaseCategory(str, Enum):
    """用例分类（SIT-09）"""
    functional = "functional"
    performance = "performance"
    security = "security"
    compatibility = "compatibility"
    usability = "usability"
    other = "other"


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


class ApiCaseKind(str, Enum):
    precondition = "precondition"
    main = "main"


class DependencyInferenceSource(str, Enum):
    auto_rule = "auto_rule"
    auto_ai = "auto_ai"
    manual = "manual"


class CaseRunType(str, Enum):
    debug = "debug"
    suite = "suite"


class ReviewStatus(str, Enum):
    init = "init"
    success = "success"
    fail = "fail"
    error = "error"


class ExecStatus(str, Enum):
    pending = "pending"      # 待执行
    running = "running"      # 运行中
    success = "success"      # 成功
    fail = "fail"            # 失败
    error = "error"          # 错误


class TaskSuiteType(str, Enum):
    api = "api"
    functional = "functional"
    ui = "ui"


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class RunMode(str, Enum):
    serial = "serial"
    parallel = "parallel"


class DefectSeverity(str, Enum):
    minor = "minor"
    normal = "normal"
    serious = "serious"
    critical = "critical"


class DefectPriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class DefectCategory(str, Enum):
    functional = "functional"
    performance = "performance"
    ui = "ui"
    compatibility = "compatibility"
    security = "security"
    other = "other"


class DefectStatus(str, Enum):
    init = "init"
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class DefectSourceType(str, Enum):
    api_case = "api_case"
    functional_case = "functional_case"
    manual = "manual"


class DefectHistoryAction(str, Enum):
    status_change = "status_change"
    field_update = "field_update"
    comment_added = "comment_added"
    created = "created"


class SuiteCaseType(str, Enum):
    api = "api"
    functional = "functional"


class CaseRunStatus(str, Enum):
    running = "running"
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
    multi_interface = "multi_interface"


class SessionStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class SourceChannel(str, Enum):
    agent_center = "agent_center"
    interface_detail = "interface_detail"
    legacy = "legacy"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"
    system = "system"


class MessageType(str, Enum):
    text = "text"
    custom = "custom"
    tool_call = "tool_call"
    tool_result = "tool_result"


class ProjectMemberRole(int, Enum):
    def __new__(cls, value: int, label: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj

    viewer = (0, "项目查看者")
    editor = (1, "项目编辑者")
    owner = (2, "项目管理员")


def project_member_role_label(role: int) -> str:
    try:
        return ProjectMemberRole(role).label
    except ValueError:
        return "未知角色"
