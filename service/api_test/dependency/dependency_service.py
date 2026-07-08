"""接口测试模块 - dependency/dependency_service

业务逻辑服务
"""
from service.api_test.dependency.dependency_schemas import (
    DependencyEdgeOut,
    DependencyListOut,
    DependencyReplaceRequest,
    DocPreviewOut,
)
from service.api_test.dependency.merge_service import DependencyMergeService
from service.api_test.dependency.schemas import DependencyEdgeDraft
from service.api_test.interface.interface_service import InterfaceService
from service.api_test.models import ApiDependency, ApiDependencyGroup
from service.api_test.permissions import ensure_api_editor, ensure_api_viewer
from service.api_test.shared.interface_doc import interface_to_doc_dict
from service.core.exceptions import AppException
from service.user.models import User


class DependencyService:
    @classmethod
    async def get_doc_preview(cls, user: User, interface_id: int) -> DocPreviewOut:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_viewer(iface.project_id, user)
        return DocPreviewOut(
            interface_id=iface.id,
            source=iface.source.value,
            source_document_id=iface.source_document_id,
            source_document_version_id=iface.source_document_version_id,
            doc=interface_to_doc_dict(iface),
            updated_at=iface.updated_at,
        )

    @classmethod
    async def list_dependencies(
        cls, user: User, interface_id: int
    ) -> DependencyListOut:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_viewer(iface.project_id, user)
        group = await ApiDependencyGroup.get_or_none(target_api_id=iface.id)
        if group is None:
            return DependencyListOut(
                target_api_id=iface.id,
                dependency_group_id=None,
                edges=[],
            )
        deps = (
            await ApiDependency.filter(dependency_group_id=group.id)
            .order_by("seq")
            .prefetch_related("to_api")
        )
        edges = [
            DependencyEdgeOut(
                id=d.id,
                from_api_id=d.from_api_id,
                to_api_id=d.to_api_id,
                seq=d.seq,
                param_map=d.param_map,
                required=d.required,
                inference_source=d.inference_source,
                confidence=d.confidence,
                to_api_method=d.to_api.method,
                to_api_path=d.to_api.path,
                to_api_summary=d.to_api.summary,
            )
            for d in deps
        ]
        return DependencyListOut(
            target_api_id=iface.id,
            dependency_group_id=group.id,
            edges=edges,
        )

    @classmethod
    async def replace_dependencies(
        cls, user: User, interface_id: int, data: DependencyReplaceRequest
    ) -> DependencyListOut:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_editor(iface.project_id, user)
        seqs = [e.seq for e in data.edges]
        if len(seqs) != len(set(seqs)):
            raise AppException("依赖顺序 seq 不能重复", 400)
        drafts: list[tuple[int, DependencyEdgeDraft]] = []
        for edge in sorted(data.edges, key=lambda e: e.seq):
            drafts.append(
                (
                    edge.to_api_id,
                    DependencyEdgeDraft(
                        to_method="",
                        to_path="",
                        seq=edge.seq,
                        param_map=edge.param_map,
                        inference_source="manual",
                        required=edge.required,
                    ),
                )
            )
        await DependencyMergeService.merge_edges(
            iface.id,
            iface.project_id,
            drafts,
            user_id=user.id,
            manual=True,
        )
        return await cls.list_dependencies(user, interface_id)

    @classmethod
    async def reanalyze(cls, user: User, interface_id: int) -> DependencyListOut:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_editor(iface.project_id, user)
        await DependencyMergeService.infer_and_persist(
            iface.project_id, [iface.id], user_id=user.id, use_ai=True
        )
        return await cls.list_dependencies(user, interface_id)
