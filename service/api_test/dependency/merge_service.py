from service.api_test.dependency.ai_analyzer import AiDependencyAnalyzer
from service.api_test.dependency.rule_inferencer import RuleInferencer
from service.api_test.dependency.schemas import DependencyEdgeDraft
from service.api_test.interface.models import ApiInterface
from service.api_test.models import ApiDependency, ApiDependencyGroup
from service.api_test.shared.interface_doc import interface_to_doc_dict
from service.core.enums import DependencyInferenceSource
from service.core.exceptions import AppException


class DependencyMergeService:
    @classmethod
    async def infer_and_persist(
        cls,
        project_id: int,
        target_interface_ids: list[int],
        *,
        user_id: int | None = None,
        use_ai: bool = False,
    ) -> tuple[list[int], list[str]]:
        errors: list[str] = []
        if not target_interface_ids:
            return [], errors

        candidates = await ApiInterface.filter(
            project_id=project_id, is_current=True
        ).all()
        candidate_docs = [interface_to_doc_dict(c) | {"id": c.id} for c in candidates]
        id_by_key = {f"{c.method}:{c.path}": c.id for c in candidates}
        # v2-L3: 收集所有已有边用于环检测
        from service.api_test.models import ApiDependency as _Dep
        existing_edges_raw = await _Dep.all().values("from_api_id", "to_api_id")
        all_edges_list = [
            {"from_api_id": e["from_api_id"], "to_api_id": e["to_api_id"]}
            for e in existing_edges_raw
        ]

        for target_id in target_interface_ids:
            target = await ApiInterface.get_or_none(id=target_id, is_current=True)
            if target is None:
                errors.append(f"interface {target_id} not found")
                continue
            target_doc = interface_to_doc_dict(target)
            drafts = RuleInferencer.infer_for_target(
                target_doc,
                [d for d in candidate_docs if d["id"] != target.id],
            )
            if use_ai and not drafts:
                ai_drafts = await AiDependencyAnalyzer.analyze(
                    target_doc,
                    [d for d in candidate_docs if d["id"] != target.id],
                )
                drafts.extend(ai_drafts)

            resolved: list[tuple[int, DependencyEdgeDraft]] = []
            for draft in drafts:
                to_id = id_by_key.get(f"{draft.to_method.upper()}:{draft.to_path}")
                if to_id is None:
                    errors.append(
                        f"{target.method} {target.path}: prerequisite "
                        f"{draft.to_method} {draft.to_path} not found"
                    )
                    continue
                resolved.append((to_id, draft))

            # v2-L3: 环检测 — 在写入前检查新边是否会形成环
            if resolved:
                test_edges = list(all_edges_list) + [
                    {"from_api_id": target_id, "to_api_id": to_id}
                    for to_id, _ in resolved
                ]
                has_cycle = RuleInferencer.detect_cycle(target_id, test_edges)
                if has_cycle:
                    errors.append(
                        f"{target.method} {target.path}: 检测到循环依赖，跳过保存"
                    )
                    continue

            await cls.merge_edges(
                target_id,
                project_id,
                resolved,
                user_id=user_id,
            )
            # 更新all_edges_list用于后续目标的检测
            all_edges_list.extend([
                {"from_api_id": target_id, "to_api_id": to_id}
                for to_id, _ in resolved
            ])
        return target_interface_ids, errors

    @classmethod
    async def merge_edges(
        cls,
        target_interface_id: int,
        project_id: int,
        edges: list[tuple[int, DependencyEdgeDraft]],
        *,
        user_id: int | None = None,
        manual: bool = False,
    ) -> ApiDependencyGroup:
        target = await ApiInterface.get(id=target_interface_id)
        group, _ = await ApiDependencyGroup.get_or_create(
            target_api_id=target.id,
            defaults={
                "name": f"{target.method} {target.path}",
                "project_id": project_id,
                "module_id": target.module_id,
                "created_by_id": user_id,
            },
        )
        if group.name != f"{target.method} {target.path}":
            group.name = f"{target.method} {target.path}"
            await group.save(update_fields=["name", "updated_at"])

        if manual:
            await ApiDependency.filter(dependency_group_id=group.id).delete()
        else:
            await ApiDependency.filter(dependency_group_id=group.id).exclude(
                inference_source=DependencyInferenceSource.manual
            ).delete()

        source = (
            DependencyInferenceSource.manual
            if manual
            else DependencyInferenceSource.auto_rule
        )
        for to_api_id, draft in edges:
            inf_source = (
                DependencyInferenceSource.manual
                if manual
                else DependencyInferenceSource(draft.inference_source)
            )
            await ApiDependency.create(
                dependency_group_id=group.id,
                from_api_id=target.id,
                to_api_id=to_api_id,
                seq=draft.seq,
                param_map=draft.param_map,
                required=draft.required,
                inference_source=inf_source,
                confidence=draft.confidence,
            )
        return group
