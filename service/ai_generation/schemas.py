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
    id: str
    label: str
    placeholder: str


class AgentMetaOut(BaseModel):
    functional_prompt_templates: list[PromptTemplateItem]
    api_prompt_templates: list[PromptTemplateItem]
    single_interface_only: bool = True
    history_limit: int = 10


class FunctionalCreateSessionRequest(BaseModel):
    project_id: int = Field(..., ge=1)
    knowledge_document_id: int | None = Field(default=None, ge=1)
    user_prompt: str | None = None
    module_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, max_length=200)


class ApiCreateSessionRequest(BaseModel):
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
    project_id: int = Field(..., ge=1)
    knowledge_document_id: int | None = Field(default=None, ge=1)
    user_prompt: str | None = None
    module_id: int | None = Field(default=None, ge=1)


class FunctionalPreviewUpdateRequest(BaseModel):
    output_payload: dict[str, Any]


class FunctionalSaveRequest(BaseModel):
    catalog_id: int = Field(..., ge=1)
    case_indexes: list[int] = Field(..., min_length=1)


class ApiGenerateFromInterfaceRequest(BaseModel):
    interface_id: int = Field(..., ge=1)
    user_prompt: str | None = None
    environment_id: int | None = Field(default=None, ge=1)


class ApiGenerateFromDocRequest(BaseModel):
    project_id: int = Field(..., ge=1)
    api_doc_text: str = Field(..., min_length=1)
    user_prompt: str | None = None
    module_id: int | None = Field(default=None, ge=1)


# ---------- Multi-interface pipeline schemas ----------

class InterfaceBaseCasesEdit(BaseModel):
    index: int
    selected_indexes: list[int] = Field(..., min_length=0)
    edited_cases: list[dict] | None = None


class SaveBaseCasesRequest(BaseModel):
    environment_id: int | None = Field(default=None, ge=1)
    interfaces: list[InterfaceBaseCasesEdit]


class PhaseInfo(BaseModel):
    id: int
    name: str
    status: str


class PipelineProgressOut(BaseModel):
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
