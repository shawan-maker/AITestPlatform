from service.core.deps import get_project_or_404
from service.core.exceptions import AppException
from service.knowledge.document.models import KnowledgeDocument
from service.project.permissions import ensure_project_editor, ensure_project_viewer
from service.user.models import User


async def ensure_document_viewer(document_id: int, user: User) -> KnowledgeDocument:
    document = await KnowledgeDocument.get_or_none(id=document_id)
    if document is None:
        raise AppException("知识库文档不存在", 404)
    await get_project_or_404(document.project_id)
    await ensure_project_viewer(document.project_id, user)
    return document


async def ensure_document_editor(document_id: int, user: User) -> KnowledgeDocument:
    document = await ensure_document_viewer(document_id, user)
    await ensure_project_editor(document.project_id, user)
    return document
