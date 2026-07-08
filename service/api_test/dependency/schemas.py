"""接口测试模块 - dependency/schemas

请求/响应 Schema 定义
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DependencyEdgeDraft:
    """依赖edgedraft"""
    to_method: str
    to_path: str
    seq: int
    param_map: dict[str, Any] | None = None
    inference_source: str = "auto_rule"
    confidence: float | None = 1.0
    required: bool = True


@dataclass
class DependencyResolveResult:
    """依赖解析结果"""
    ordered_to_apis: list[Any] = field(default_factory=list)
    precoditions_summaries: list[str] = field(default_factory=list)
    precoditions_api_doc: list[dict] = field(default_factory=list)
    param_maps: list[dict | None] = field(default_factory=list)
    dependency_group_id: int | None = None
