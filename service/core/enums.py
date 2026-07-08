from enum import Enum


class ConfigType(str, Enum):
    """配置类型"""
    scalar = "scalar"
    json = "json"
    secret = "secret"


class DbType(str, Enum):
    """db类型"""
    mysql = "mysql"
    sqlserver = "sqlserver"
    oracle = "oracle"


class DebugVarSource(str, Enum):
    """调试var来源"""
    engine = "engine"
    manual = "manual"


class RagType(str, Enum):
    """rag类型"""
    api = "api"


class KnowledgeDocType(str, Enum):
    """knowledge文档类型"""
    requirement = "requirement"
    api_doc = "api_doc"
    other = "other"


class IndexStatus(str, Enum):
    """index状态"""
    pending = "pending"
    indexing = "indexing"
    parsing = "parsing"
    indexed = "indexed"
    failed = "failed"
    na = "na"


class ParseMode(str, Enum):
    """解析mode"""
    openapi = "openapi"
    swagger = "swagger"
    ai = "ai"


class ParseStatus(str, Enum):
    """解析状态"""
    pending = "pending"
    parsing = "parsing"
    parsed = "parsed"
    failed = "failed"


class ActualParseRoute(str, Enum):
    """actual解析route"""
    ai_text = "ai_text"
    ai_multimodal = "ai_multimodal"
    swagger = "swagger"
    openapi = "openapi"
    auto_text = "auto_text"


class RagBackend(str, Enum):
    """ragbackend"""
    rag_client = "rag_client"
    rag_manager = "rag_manager"


class FunctionalExecResult(str, Enum):
    """functionalexec结果"""
    pending = "pending"
    passed = "passed"
    failed = "failed"
    blocked = "blocked"
    skipped = "skipped"


class SourceType(str, Enum):
    """来源类型"""
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
    """functional用例状态"""
    design = "design"
    ready = "ready"
    smoke = "smoke"
    regression = "regression"
    obsolete = "obsolete"


class ContentFormat(str, Enum):
    """contentformat"""
    text = "text"
    json = "json"


class ApiInterfaceSource(str, Enum):
    """API接口来源"""
    swagger = "swagger"
    openapi = "openapi"
    rag = "rag"
    manual = "manual"
    ai = "ai"


class ApiBaseCaseStatus(str, Enum):
    """API基础用例状态"""
    draft = "draft"
    approved = "approved"
    archived = "archived"


class ApiTestCaseType(str, Enum):
    """API测试用例类型"""
    api = "api"
    business = "business"


class ApiCaseKind(str, Enum):
    """API用例kind"""
    precondition = "precondition"
    main = "main"


class DependencyInferenceSource(str, Enum):
    """依赖inference来源"""
    auto_rule = "auto_rule"
    auto_ai = "auto_ai"
    manual = "manual"


class CaseRunType(str, Enum):
    """用例执行类型"""
    debug = "debug"
    suite = "suite"


class ReviewStatus(str, Enum):
    """review状态"""
    init = "init"
    success = "success"
    fail = "fail"
    error = "error"


class ExecStatus(str, Enum):
    """exec状态"""
    pending = "pending"      # 待执行
    running = "running"      # 运行中
    success = "success"      # 成功
    fail = "fail"            # 失败
    error = "error"          # 错误


class TaskSuiteType(str, Enum):
    """任务套件类型"""
    api = "api"
    functional = "functional"
    ui = "ui"


class RunStatus(str, Enum):
    """执行状态"""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class RunMode(str, Enum):
    """执行mode"""
    serial = "serial"
    parallel = "parallel"


class DefectSeverity(str, Enum):
    """缺陷严重程度"""
    minor = "minor"
    normal = "normal"
    serious = "serious"
    critical = "critical"


class DefectPriority(str, Enum):
    """缺陷优先级"""
    high = "high"
    medium = "medium"
    low = "low"


class DefectCategory(str, Enum):
    """缺陷分类"""
    functional = "functional"
    performance = "performance"
    ui = "ui"
    compatibility = "compatibility"
    security = "security"
    other = "other"


class DefectStatus(str, Enum):
    """缺陷状态"""
    init = "init"
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class DefectSourceType(str, Enum):
    """缺陷来源类型"""
    api_case = "api_case"
    functional_case = "functional_case"
    manual = "manual"


class DefectHistoryAction(str, Enum):
    """缺陷历史action"""
    status_change = "status_change"
    field_update = "field_update"
    comment_added = "comment_added"
    created = "created"


class SuiteCaseType(str, Enum):
    """套件用例类型"""
    api = "api"
    functional = "functional"


class CaseRunStatus(str, Enum):
    """用例执行状态"""
    running = "running"
    success = "success"
    fail = "fail"
    error = "error"


class GenType(str, Enum):
    """gen类型"""
    functional = "functional"
    api_base = "api_base"
    api_runnable = "api_runnable"


class InputRefType(str, Enum):
    """inputref类型"""
    requirement = "requirement"
    interface = "interface"
    api_doc = "api_doc"
    multi_iface = "multi_iface"


class SessionStatus(str, Enum):
    """会话状态"""
    pending = "pending"
    running = "running"
    confirming = "confirm"  # 等待用户确认/编辑
    success = "success"
    failed = "failed"


class SourceChannel(str, Enum):
    """来源channel"""
    agent_center = "agent_center"
    interface_detail = "interface_detail"
    legacy = "legacy"


class MessageRole(str, Enum):
    """消息role"""
    user = "user"
    assistant = "assistant"
    tool = "tool"
    system = "system"


class MessageType(str, Enum):
    """消息类型"""
    text = "text"
    custom = "custom"
    tool_call = "tool_call"
    tool_result = "tool_result"


class ProjectMemberRole(int, Enum):
    """项目成员role"""
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
