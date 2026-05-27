"""Agent hub request/response DTOs (thin wrappers over domain schemas)."""

from typing import Any

from pydantic import BaseModel, Field

from service.api_test.case.schemas import (
    ApiConfirmRequest,
    ApiConfirmResult,
    ApiGenerationSessionOut,
    ApiSessionPreviewUpdateRequest,
    GeneratePreviewResult,
)
from service.functional_test.case.schemas import (
    GenerationSaveResult,
    GenerationSessionOut,
)


class PromptTemplateItem(BaseModel):
    id: str
    label: str
    placeholder: str


class AgentMetaOut(BaseModel):
    functional_prompt_templates: list[PromptTemplateItem]
    api_prompt_templates: list[PromptTemplateItem]
    single_interface_only: bool = True


class FunctionalGenerateRequest(BaseModel):
    project_id: int = Field(..., ge=1)
    requirement_text: str | None = None
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


__all__ = [
    "AgentMetaOut",
    "ApiConfirmRequest",
    "ApiConfirmResult",
    "ApiGenerateFromDocRequest",
    "ApiGenerateFromInterfaceRequest",
    "ApiGenerationSessionOut",
    "ApiSessionPreviewUpdateRequest",
    "FunctionalGenerateRequest",
    "FunctionalPreviewUpdateRequest",
    "FunctionalSaveRequest",
    "GeneratePreviewResult",
    "GenerationSaveResult",
    "GenerationSessionOut",
    "PromptTemplateItem",
]
