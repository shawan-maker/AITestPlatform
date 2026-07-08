"""测试管理模块 - task/case_relation_service

业务逻辑服务
"""
from __future__ import annotations

from service.core.enums import SuiteCaseType, TaskSuiteType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.functional_test.case.models import FunctionalCase, FunctionalCaseCatalog
from service.test_management.models import TaskCaseRelation, TestTask
from service.test_management.permissions import ensure_tm_editor, ensure_tm_viewer
from service.test_management.shared.relation_ops import replace_relations
from service.test_management.task.schemas import (
    PaginatedTaskCases,
    TaskCaseBatchRemoveRequest,
    TaskCaseRelationOut,
    TaskCaseReplaceRequest,
    TaskCaseTreeNode,
)
from service.user.models import User


class TaskCaseRelationService:
    @classmethod
    async def _get_task_or_404(cls, task_id: int) -> TestTask:
        task = await TestTask.get_or_none(id=task_id)
        if task is None:
            raise AppException("任务不存在", 404)
        return task

    @classmethod
    async def _ensure_functional_task(cls, task: TestTask) -> None:
        if task.type != TaskSuiteType.functional:
            raise AppException("仅功能任务支持直挂用例", 400)

    @classmethod
    async def _validate_case_ids(cls, project_id: int, case_ids: list[int]) -> None:
        if not case_ids:
            return
        count = await FunctionalCase.filter(
            id__in=case_ids, project_id=project_id
        ).count()
        if count != len(set(case_ids)):
            raise AppException("部分功能用例不存在或不属于当前项目", 400)

    @classmethod
    async def _build_case_out(cls, rel: TaskCaseRelation) -> TaskCaseRelationOut:
        case = await FunctionalCase.get_or_none(id=rel.case_id)
        module_name = None
        if case and case.module_id:
            from service.project.models import ProjectModule
            mod = await ProjectModule.get_or_none(id=case.module_id)
            if mod:
                module_name = mod.name
        return TaskCaseRelationOut(
            id=rel.id,
            case_id=rel.case_id,
            case_order=rel.case_order,
            case_name=case.case_name if case else None,
            case_no=case.case_no if case else None,
            priority=case.priority if case else None,
            case_category=case.case_category if case else None,
            catalog_id=case.catalog_id if case else None,
            module_id=case.module_id if case else None,
            module_name=module_name,
        )

    @classmethod
    async def list(
        cls, user: User, task_id: int, *, page: int = 1, page_size: int = 20
    ) -> PaginatedTaskCases:
        task = await cls._get_task_or_404(task_id)
        await cls._ensure_functional_task(task)
        await ensure_tm_viewer(task.project_id, user)
        qs = TaskCaseRelation.filter(
            task_id=task_id, case_type=SuiteCaseType.functional
        ).order_by("case_order", "id")
        total, items = await paginate(qs, page, page_size)
        out = [await cls._build_case_out(rel) for rel in items]
        return PaginatedTaskCases(total=total, page=page, page_size=page_size, items=out)

    @classmethod
    async def replace(cls, user: User, task_id: int, data: TaskCaseReplaceRequest) -> None:
        task = await cls._get_task_or_404(task_id)
        await cls._ensure_functional_task(task)
        await ensure_tm_editor(task.project_id, user)
        await cls._validate_case_ids(task.project_id, data.case_ids)
        items = [
            {"case_type": SuiteCaseType.functional, "case_id": cid}
            for cid in data.case_ids
        ]
        await replace_relations(TaskCaseRelation, "task_id", task_id, items)

    @classmethod
    async def batch_remove(cls, user: User, task_id: int, data: TaskCaseBatchRemoveRequest) -> None:
        task = await cls._get_task_or_404(task_id)
        await cls._ensure_functional_task(task)
        await ensure_tm_editor(task.project_id, user)
        await TaskCaseRelation.filter(
            task_id=task_id,
            case_type=SuiteCaseType.functional,
            case_id__in=data.case_ids,
        ).delete()

    @classmethod
    async def reorder(cls, user: User, task_id: int, ordered_case_ids: list[int]) -> None:
        task = await cls._get_task_or_404(task_id)
        await cls._ensure_functional_task(task)
        await ensure_tm_editor(task.project_id, user)
        relations = await TaskCaseRelation.filter(
            task_id=task_id, case_type=SuiteCaseType.functional
        ).all()
        rel_by_case = {r.case_id: r for r in relations}
        if set(rel_by_case.keys()) != set(ordered_case_ids):
            raise AppException("排序用例与现有关联不匹配", 400)
        for idx, case_id in enumerate(ordered_case_ids, start=1):
            rel = rel_by_case[case_id]
            rel.case_order = idx
            await rel.save(update_fields=["case_order"])

    @classmethod
    async def get_tree(cls, user: User, task_id: int) -> list[TaskCaseTreeNode]:
        task = await cls._get_task_or_404(task_id)
        await cls._ensure_functional_task(task)
        await ensure_tm_viewer(task.project_id, user)
        relations = await TaskCaseRelation.filter(
            task_id=task_id, case_type=SuiteCaseType.functional
        ).order_by("case_order", "id")
        case_ids = [r.case_id for r in relations]
        cases = await FunctionalCase.filter(id__in=case_ids)
        case_map = {c.id: c for c in cases}
        rel_out_map: dict[int, TaskCaseRelationOut] = {}
        catalog_case_map: dict[int | None, list[TaskCaseRelationOut]] = {}
        for rel in relations:
            out = await cls._build_case_out(rel)
            rel_out_map[rel.case_id] = out
            case = case_map.get(rel.case_id)
            cat_id = case.catalog_id if case else None
            catalog_case_map.setdefault(cat_id, []).append(out)
        catalogs = await FunctionalCaseCatalog.filter(project_id=task.project_id).order_by(
            "level", "sort_order", "id"
        )
        nodes: dict[int, TaskCaseTreeNode] = {}
        roots: list[TaskCaseTreeNode] = []
        for cat in catalogs:
            node = TaskCaseTreeNode(
                id=cat.id,
                name=cat.name,
                level=cat.level,
                parent_id=cat.parent_id,
                cases=catalog_case_map.get(cat.id, []),
            )
            nodes[cat.id] = node
        for node in nodes.values():
            if node.parent_id and node.parent_id in nodes:
                nodes[node.parent_id].children.append(node)
            elif node.parent_id is None:
                roots.append(node)
        uncategorized = catalog_case_map.get(None, [])
        if uncategorized:
            roots.append(
                TaskCaseTreeNode(
                    id=0,
                    name="未分类",
                    level=0,
                    parent_id=None,
                    cases=uncategorized,
                )
            )
        return roots
