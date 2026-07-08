"""测试管理模块 - task/suite_relation_service

业务逻辑服务
"""
from __future__ import annotations

from service.core.enums import TaskSuiteType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.test_management.models import TaskSuiteRelation, TestSuite, TestTask
from service.test_management.permissions import ensure_tm_editor, ensure_tm_viewer
from service.test_management.shared.case_count_query import count_suite_cases
from service.test_management.shared.relation_ops import replace_relations
from service.test_management.task.schemas import (
    PaginatedTaskSuites,
    TaskSuiteBatchRemoveRequest,
    TaskSuiteRelationOut,
    TaskSuiteReplaceRequest,
)
from service.user.models import User


class SuiteRelationService:
    @classmethod
    async def _get_task_or_404(cls, task_id: int) -> TestTask:
        task = await TestTask.get_or_none(id=task_id)
        if task is None:
            raise AppException("任务不存在", 404)
        return task

    @classmethod
    async def _ensure_api_task(cls, task: TestTask) -> None:
        if task.type == TaskSuiteType.functional:
            raise AppException("功能任务不支持套件关联", 400)
        if task.type == TaskSuiteType.ui:
            raise AppException("UI 任务暂未实现", 501)

    @classmethod
    async def _validate_suites(cls, project_id: int, task_type: TaskSuiteType, suite_ids: list[int]) -> None:
        if not suite_ids:
            return
        suites = await TestSuite.filter(id__in=suite_ids, project_id=project_id)
        if len(suites) != len(set(suite_ids)):
            raise AppException("部分套件不存在或不属于当前项目", 400)
        for suite in suites:
            if suite.type != task_type:
                raise AppException(f"套件 {suite.suite_name} 类型与任务不匹配", 400)

    @classmethod
    async def list(
        cls, user: User, task_id: int, *, page: int = 1, page_size: int = 20
    ) -> PaginatedTaskSuites:
        task = await cls._get_task_or_404(task_id)
        await cls._ensure_api_task(task)
        await ensure_tm_viewer(task.project_id, user)
        qs = TaskSuiteRelation.filter(task_id=task_id).order_by("suite_order", "id")
        total, items = await paginate(qs, page, page_size)
        suite_ids = [r.suite_id for r in items]
        counts = await count_suite_cases(suite_ids)
        suite_map = {
            s.id: s
            for s in await TestSuite.filter(id__in=suite_ids)
        }
        out = [
            TaskSuiteRelationOut(
                id=r.id,
                suite_id=r.suite_id,
                suite_name=suite_map[r.suite_id].suite_name,
                suite_order=r.suite_order,
                case_count=counts.get(r.suite_id, 0),
            )
            for r in items
            if r.suite_id in suite_map
        ]
        return PaginatedTaskSuites(total=total, page=page, page_size=page_size, items=out)

    @classmethod
    async def replace(cls, user: User, task_id: int, data: TaskSuiteReplaceRequest) -> None:
        task = await cls._get_task_or_404(task_id)
        await cls._ensure_api_task(task)
        await ensure_tm_editor(task.project_id, user)
        await cls._validate_suites(task.project_id, task.type, data.suite_ids)
        items = [{"suite_id": sid} for sid in data.suite_ids]
        await replace_relations(
            TaskSuiteRelation, "task_id", task_id, items, order_key="suite_order"
        )

    @classmethod
    async def batch_remove(cls, user: User, task_id: int, data: TaskSuiteBatchRemoveRequest) -> None:
        task = await cls._get_task_or_404(task_id)
        await cls._ensure_api_task(task)
        await ensure_tm_editor(task.project_id, user)
        await TaskSuiteRelation.filter(task_id=task_id, suite_id__in=data.suite_ids).delete()

    @classmethod
    async def reorder(cls, user: User, task_id: int, ordered_suite_ids: list[int]) -> None:
        task = await cls._get_task_or_404(task_id)
        await cls._ensure_api_task(task)
        await ensure_tm_editor(task.project_id, user)
        relations = await TaskSuiteRelation.filter(task_id=task_id).all()
        rel_by_suite = {r.suite_id: r for r in relations}
        if set(rel_by_suite.keys()) != set(ordered_suite_ids):
            raise AppException("排序套件与现有关联不匹配", 400)
        for idx, suite_id in enumerate(ordered_suite_ids, start=1):
            rel = rel_by_suite[suite_id]
            rel.suite_order = idx
            await rel.save(update_fields=["suite_order"])
