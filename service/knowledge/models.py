"""Re-export ORM models for Tortoise and backward-compatible imports."""

from service.knowledge.document.models import (
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeWorkspace,
)

__all__ = [
    "KnowledgeWorkspace",
    "KnowledgeDocument",
    "KnowledgeDocumentVersion",
]
