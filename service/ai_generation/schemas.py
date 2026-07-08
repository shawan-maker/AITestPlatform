"""Agent hub request/response DTOs (thin wrappers over domain schemas)."""

from typing import Any

from pydantic import BaseModel, Field

from service.ai_generation.session_schemas import (
    AIGenerationPreviewUpdateRequest,
    AIGenerationSessionOut,
)
from service.api_test.case.schemas import (
    ApiConfirmRequest,
    ApiConfirmResult,
    GeneratePreviewResult,
)
from service.functional_test.case.schemas import GenerationSaveResult


class PromptTemplateItem(BaseModel):
    """prompttemplateitem"""
    id: str
    label: str
    placeholder: str


class AgentMetaOut(BaseModel):
    """智能体metaout"""
    functional_prompt_templates: list[PromptTemplateItem]
    api_prompt_templates: list[PromptTemplateItem]
    single_interface_only: bool = True
    history_limit: int = 10


class FunctionalCreateSessionRequest(BaseModel):
    """functional创建会话请求"""
    project_id: int = Field(..., ge=1)
    knowledge_document_id: int | None = Field(default=None, ge=1)
    user_prompt: str | None = None
    module_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, max_length=200)


class ApiCreateSessionRequest(BaseModel):
    """API创建会话请求"""
    project_id: int = Field(..., ge=1)
    interface_id: int | None = Field(default=None, ge=1)
    interface_ids: list[int] | None = None
    api_doc_text: str | None = None
    user_prompt: str | None = None
    environment_id: int | None = Field(default=None, ge=1)
    module_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, max_length=200)
    mode: str | None = None  # "from_doc" | "from_interfaces" | None (legacy single)


class FunctionalGenerateRequest(BaseModel):
    """functional生成请求"""
    project_id: int = Field(..., ge=1)
    knowledge_document_id: int | None = Field(default=None, ge=1)
    user_prompt: str | None = None
    module_id: int | None = Field(default=None, ge=1)


class FunctionalPreviewUpdateRequest(BaseModel):
    """functionalpreview更新请求"""
    output_payload: dict[str, Any]


class FunctionalSaveRequest(BaseModel):
    """functional保存请求"""
    catalog_id: int = Field(..., ge=1)
    case_indexes: list[int] = Field(..., min_length=1)


class ApiGenerateFromInterfaceRequest(BaseModel):
    """API生成from接口请求"""
    interface_id: int = Field(..., ge=1)
    user_prompt: str | None = None
    environment_id: int | None = Field(default=None, ge=1)


class ApiGenerateFromDocRequest(BaseModel):
    """API生成from文档请求"""
    project_id: int = Field(..., ge=1)
    api_doc_text: str = Field(..., min_length=1)
    user_prompt: str | None = None
    module_id: int | None = Field(default=None, ge=1)


# ---------- Multi-interface pipeline schemas ----------

class InterfaceBaseCasesEdit(BaseModel):
    """接口基础casesedit"""
    index: int
    selected_indexes: list[int] = Field(..., min_length=0)
    edited_cases: list[dict] | None = None


class SaveBaseCasesRequest(BaseModel):
    """保存基础cases请求"""
    environment_id: int | None = Field(default=None, ge=1)
    interfaces: list[InterfaceBaseCasesEdit]


class PhaseInfo(BaseModel):
    """phaseinfo"""
    id: int
    name: str
    status: str


class PipelineProgressOut(BaseModel):
    """管道进度out"""
    current_phase: int
    phases: list[PhaseInfo]
    summary: dict | None = None


# Backward-compatible aliases
GenerationSessionOut = AIGenerationSessionOut
ApiGenerationSessionOut = AIGenerationSessionOut
ApiSessionPreviewUpdateRequest = AIGenerationPreviewUpdateRequest


__all__ = [
    "AgentMetaOut",
    "ApiCreateSessionRequest",
    "AIGenerationPreviewUpdateRequest",
    "AIGenerationSessionOut",
    "ApiConfirmRequest",
    "ApiConfirmResult",
    "ApiGenerateFromDocRequest",
    "ApiGenerateFromInterfaceRequest",
    "ApiGenerationSessionOut",
    "ApiSessionPreviewUpdateRequest",
    "FunctionalCreateSessionRequest",
    "FunctionalGenerateRequest",
    "FunctionalPreviewUpdateRequest",
    "FunctionalSaveRequest",
    "GeneratePreviewResult",
    "GenerationSaveResult",
    "GenerationSessionOut",
    "InterfaceBaseCasesEdit",
    "PipelineProgressOut",
    "PromptTemplateItem",
    "SaveBaseCasesRequest",
]
