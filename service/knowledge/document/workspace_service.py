from service.core.enums import KnowledgeDocType, RagType
from service.core.exceptions import AppException
from service.knowledge.document.models import KnowledgeWorkspace
from service.project.models import Project


class WorkspaceService:
    @staticmethod
    def _rag_type_for_doc_type(doc_type: KnowledgeDocType) -> RagType:
        if doc_type == KnowledgeDocType.api_doc:
            return RagType.api
        # 其他类型（如 other）也使用 api RAG
        return RagType.api

    @classmethod
    async def ensure_workspace(cls, project: Project, doc_type: KnowledgeDocType) -> KnowledgeWorkspace:
        rag_type = cls._rag_type_for_doc_type(doc_type)
        workspace = await KnowledgeWorkspace.get_or_none(
            project_id=project.id,
            rag_type=rag_type,
        )
        if workspace is not None:
            return workspace
        return await KnowledgeWorkspace.create(
            project_id=project.id,
            workspace_key=project.name,
            rag_type=rag_type,
        )
