from __future__ import annotations

from service.core.enums import RunMode, RunStatus, TaskSuiteType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.test_environment.models import TestEnvironment
from service.test_management.models import TaskSuiteRelation, TestSuite, TestTask
from service.test_management.permissions import ensure_tm_editor, ensure_tm_viewer
from service.test_management.shared.case_count_query import (
    count_suite_cases,
    count_task_api_cases,
    count_task_functional_cases,
)
from service.test_management.shared.last_run_query import (
    fetch_task_last_runs,
    last_run_brief_from_task_run,
)
from service.test_management.shared.name_validator import ensure_unique_task_name
from service.test_management.shared.schemas_common import LastRunBrief
from service.test_management.task.schemas import (
    PaginatedTasks,
    TaskCreateRequest,
    TaskDetailOut,
    TaskListQuery,
    TaskOut,
    TaskSuiteBrief,
    TaskUpdateRequest,
)
from service.project.models import ProjectModule
from service.user.models import User


class TaskService:
    @classmethod
    async def _get_task_or_404(cls, task_id: int) -> TestTask:
        task = await TestTask.get_or_none(id=task_id)
        if task is None:
            raise AppException("任务不存在", 404)
        return task

    @classmethod
    async def _validate_module(cls, project_id: int, module_id: int | None) -> None:
        if module_id is None:
            return
        if not await ProjectModule.filter(id=module_id, project_id=project_id).exists():
            raise AppException("项目模块不存在", 404)

    @classmethod
    async def _validate_environment(cls, project_id: int, environment_id: int | None) -> None:
        if environment_id is None:
            return
        if not await TestEnvironment.filter(id=environment_id, project_id=project_id).exists():
            raise AppException("测试环境不存在", 404)

    @classmethod
    def _reject_ui_not_implemented(cls, task_type: TaskSuiteType) -> None:
        if task_type == TaskSuiteType.ui:
            raise AppException("UI 任务暂未实现", 501)

    @classmethod
    async def _validate_task_fields(
        cls,
        project_id: int,
        task_type: TaskSuiteType,
        environment_id: int | None,
        run_mode: RunMode | None,
    ) -> None:
        if task_type in (TaskSuiteType.api, TaskSuiteType.ui):
            if environment_id is None:
                raise AppException("API/UI 任务必须指定测试环境", 400)
            if run_mode is None:
                raise AppException("API/UI 任务必须指定运行方式", 400)

    @classmethod
    async def _get_case_count(cls, task: TestTask) -> int:
        if task.type == TaskSuiteType.functional:
            counts = await count_task_functional_cases([task.id])
        else:
            counts = await count_task_api_cases([task.id])
        return counts.get(task.id, 0)

    @classmethod
    def _to_out(cls, task: TestTask, *, case_count: int, last_run: LastRunBrief, environment_name: str | None = None) -> TaskOut:
        return TaskOut(
            id=task.id,
            project_id=task.project_id,
            task_name=task.task_name,
            description=task.description,
            type=task.type,
            module_id=task.module_id,
            environment_id=task.environment_id,
            environment_name=environment_name,
            run_mode=task.run_mode,
            case_count=case_count,
            last_run=last_run,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @classmethod
    async def _resolve_env_names(cls, task_ids: list[int]) -> dict[int, str]:
        """Batch resolve environment names for tasks."""
        tasks = await TestTask.filter(id__in=task_ids, environment_id__isnull=False).values("id", "environment_id")
        env_ids = list({t["environment_id"] for t in tasks if t["environment_id"]})
        if not env_ids:
            return {}
        envs = await TestEnvironment.filter(id__in=env_ids).values("id", "env_name")
        env_map = {e["id"]: e["env_name"] for e in envs}
        return {t["id"]: env_map.get(t["environment_id"]) for t in tasks if t["environment_id"]}

    @classmethod
    async def list(cls, user: User, query: TaskListQuery) -> PaginatedTasks:
        await ensure_tm_viewer(query.project_id, user)
        qs = TestTask.filter(project_id=query.project_id)
        if query.type is not None:
            qs = qs.filter(type=query.type)
        if query.q:
            qs = qs.filter(task_name__icontains=query.q.strip())
        if query.status is not None:
            task_ids = await cls._filter_task_ids_by_last_run_status(query.project_id, query.status)
            qs = qs.filter(id__in=task_ids or [-1])
        if query.result is not None:
            task_ids = await cls._filter_task_ids_by_result(query.project_id, query.result)
            qs = qs.filter(id__in=task_ids or [-1])
        if query.triggered_by:
            task_ids = await cls._filter_task_ids_by_executor(query.project_id, query.triggered_by)
            qs = qs.filter(id__in=task_ids or [-1])
        qs = qs.order_by("-updated_at", "-id")
        total, items = await paginate(qs, query.page, query.page_size)
        task_ids = [t.id for t in items]
        func_counts = await count_task_functional_cases(task_ids)
        api_counts = await count_task_api_cases(task_ids)
        last_runs = await fetch_task_last_runs(task_ids)
        env_names = await cls._resolve_env_names(task_ids)
        out_items = []
        for t in items:
            case_count = (
                func_counts.get(t.id, 0)
                if t.type == TaskSuiteType.functional
                else api_counts.get(t.id, 0)
            )
            out_items.append(
                cls._to_out(
                    t,
                    case_count=case_count,
                    last_run=LastRunBrief(
                        **last_run_brief_from_task_run(last_runs.get(t.id))
                    ),
                    environment_name=env_names.get(t.id),
                )
            )
        return PaginatedTasks(
            total=total, page=query.page, page_size=query.page_size, items=out_items
        )

    @classmethod
    async def _filter_task_ids_by_last_run_status(
        cls, project_id: int, status: RunStatus
    ) -> list[int]:
        tasks = await TestTask.filter(project_id=project_id).values("id")
        task_ids = [t["id"] for t in tasks]
        last_runs = await fetch_task_last_runs(task_ids)
        return [tid for tid, run in last_runs.items() if run.status == status]

    @classmethod
    async def _filter_task_ids_by_result(
        cls, project_id: int, result: str
    ) -> list[int]:
        """Filter tasks by execution result: 'success' or 'fail'."""
        tasks = await TestTask.filter(project_id=project_id).values("id")
        task_ids = [t["id"] for t in tasks]
        last_runs = await fetch_task_last_runs(task_ids)
        matched = []
        for tid, run in last_runs.items():
            if result == "success":
                if run.status == RunStatus.completed and run.total_cases > 0 and run.passed_cases == run.total_cases:
                    matched.append(tid)
            elif result == "fail":
                if run.status == RunStatus.failed:
                    matched.append(tid)
                elif run.status == RunStatus.completed and run.total_cases > 0 and run.passed_cases < run.total_cases:
                    matched.append(tid)
        return matched

    @classmethod
    async def _filter_task_ids_by_executor(
        cls, project_id: int, keyword: str
    ) -> list[int]:
        """Filter tasks by executor username keyword."""
        users = await User.filter(username__icontains=keyword.strip()).values("id")
        user_ids = [u["id"] for u in users]
        if not user_ids:
            return []
        tasks = await TestTask.filter(project_id=project_id).values("id")
        task_ids = [t["id"] for t in tasks]
        last_runs = await fetch_task_last_runs(task_ids)
        return [
            tid for tid, run in last_runs.items()
            if run.triggered_by_id in user_ids
        ]

    @classmethod
    async def create(cls, user: User, data: TaskCreateRequest) -> TaskDetailOut:
        cls._reject_ui_not_implemented(data.type)
        await ensure_tm_editor(data.project_id, user)
        await ensure_unique_task_name(data.project_id, data.task_name)
        await cls._validate_module(data.project_id, data.module_id)
        await cls._validate_environment(data.project_id, data.environment_id)
        await cls._validate_task_fields(
            data.project_id, data.type, data.environment_id, data.run_mode
        )
        task = await TestTask.create(
            project_id=data.project_id,
            module_id=data.module_id,
            environment_id=data.environment_id,
            task_name=data.task_name,
            description=data.description,
            type=data.type,
            run_mode=data.run_mode,
            created_by_id=user.id,
        )
        return await cls.get_detail(user, task.id)

    @classmethod
    async def get_detail(cls, user: User, task_id: int) -> TaskDetailOut:
        task = await cls._get_task_or_404(task_id)
        await ensure_tm_viewer(task.project_id, user)
        case_count = await cls._get_case_count(task)
        last_runs = await fetch_task_last_runs([task.id])
        env_names = await cls._resolve_env_names([task.id])
        base = cls._to_out(
            task,
            case_count=case_count,
            last_run=LastRunBrief(**last_run_brief_from_task_run(last_runs.get(task.id))),
            environment_name=env_names.get(task.id),
        )
        suites: list[TaskSuiteBrief] = []
        if task.type != TaskSuiteType.functional:
            rels = await TaskSuiteRelation.filter(task_id=task.id).prefetch_related("suite")
            suite_ids = [r.suite_id for r in rels]
            counts = await count_suite_cases(suite_ids)
            suites = [
                TaskSuiteBrief(
                    id=r.id,
                    suite_id=r.suite_id,
                    suite_name=r.suite.suite_name,
                    suite_order=r.suite_order,
                    case_count=counts.get(r.suite_id, 0),
                )
                for r in rels
            ]
        return TaskDetailOut(**base.model_dump(), suites=suites)

    @classmethod
    async def update(cls, user: User, task_id: int, data: TaskUpdateRequest) -> TaskDetailOut:
        task = await cls._get_task_or_404(task_id)
        await ensure_tm_editor(task.project_id, user)
        if data.task_name is not None:
            await ensure_unique_task_name(task.project_id, data.task_name, exclude_id=task.id)
            task.task_name = data.task_name
        if data.description is not None:
            task.description = data.description
        if data.module_id is not None:
            await cls._validate_module(task.project_id, data.module_id)
            task.module_id = data.module_id
        if data.environment_id is not None:
            await cls._validate_environment(task.project_id, data.environment_id)
            task.environment_id = data.environment_id
        if data.run_mode is not None:
            task.run_mode = data.run_mode
        await cls._validate_task_fields(
            task.project_id, task.type, task.environment_id, task.run_mode
        )
        await task.save()
        return await cls.get_detail(user, task.id)

    @classmethod
    async def delete(cls, user: User, task_id: int) -> None:
        task = await cls._get_task_or_404(task_id)
        await ensure_tm_editor(task.project_id, user)
        from service.test_execution.run.run_lock import assert_no_running_for_task

        await assert_no_running_for_task(task_id)
        await task.delete()

    @classmethod
    async def batch_delete(cls, user: User, data) -> dict:
        deleted_ids = []
        failures = []
        for item_id in data.task_ids:
            try:
                await cls.delete(user, item_id)
                deleted_ids.append(item_id)
            except AppException as e:
                failures.append({'task_id': item_id, 'message': e.message})
            except Exception as e:
                failures.append({'task_id': item_id, 'message': str(e)})
        return {'deleted_ids': deleted_ids, 'failures': failures}
