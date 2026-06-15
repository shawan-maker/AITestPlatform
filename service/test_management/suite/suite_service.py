from __future__ import annotations

from tortoise.expressions import Q

from service.core.enums import RunStatus, TaskSuiteType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.test_environment.models import TestEnvironment
from service.test_management.models import (
    SuiteCaseRelation,
    TaskSuiteRelation,
    TestSuite,
)
from service.test_management.permissions import ensure_tm_editor, ensure_tm_viewer
from service.test_management.shared.case_count_query import count_suite_cases
from service.test_management.shared.last_run_query import (
    fetch_suite_last_runs,
    last_run_brief_from_suite_run,
)
from service.test_management.shared.name_validator import ensure_unique_suite_name
from service.test_management.shared.schemas_common import LastRunBrief
from service.test_management.suite.schemas import (
    BoundTaskBrief,
    PaginatedSuites,
    SuiteCreateRequest,
    SuiteDetailOut,
    SuiteListQuery,
    SuiteOut,
    SuiteUpdateRequest,
)
from service.project.models import ProjectModule
from service.user.models import User


class SuiteService:
    @classmethod
    async def _get_suite_or_404(cls, suite_id: int) -> TestSuite:
        suite = await TestSuite.get_or_none(id=suite_id)
        if suite is None:
            raise AppException("套件不存在", 404)
        return suite

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
    def _reject_ui_not_implemented(cls, suite_type: TaskSuiteType) -> None:
        if suite_type == TaskSuiteType.ui:
            raise AppException("UI 套件暂未实现", 501)

    @classmethod
    async def _validate_api_suite_fields(
        cls, project_id: int, suite_type: TaskSuiteType, environment_id: int | None
    ) -> None:
        if suite_type == TaskSuiteType.api and environment_id is None:
            raise AppException("API 套件必须指定测试环境", 400)

    @classmethod
    def _to_out(cls, suite: TestSuite, *, case_count: int, last_run: LastRunBrief) -> SuiteOut:
        return SuiteOut(
            id=suite.id,
            project_id=suite.project_id,
            suite_name=suite.suite_name,
            description=suite.description,
            type=suite.type,
            module_id=suite.module_id,
            environment_id=suite.environment_id,
            run_mode=suite.run_mode,
            case_count=case_count,
            last_run=last_run,
            created_at=suite.created_at,
            updated_at=suite.updated_at,
        )

    @classmethod
    async def list(cls, user: User, query: SuiteListQuery) -> PaginatedSuites:
        await ensure_tm_viewer(query.project_id, user)
        qs = TestSuite.filter(project_id=query.project_id)
        if query.type is not None:
            qs = qs.filter(type=query.type)
        if query.q:
            qs = qs.filter(suite_name__icontains=query.q.strip())
        if query.status is not None:
            suite_ids_with_status = await cls._filter_suite_ids_by_last_run_status(
                query.project_id, query.status
            )
            qs = qs.filter(id__in=suite_ids_with_status or [-1])
        qs = qs.order_by("-updated_at", "-id")
        total, items = await paginate(qs, query.page, query.page_size)
        suite_ids = [s.id for s in items]
        case_counts = await count_suite_cases(suite_ids)
        last_runs = await fetch_suite_last_runs(suite_ids)
        out_items = [
            cls._to_out(
                s,
                case_count=case_counts.get(s.id, 0),
                last_run=LastRunBrief(**last_run_brief_from_suite_run(last_runs.get(s.id))),
            )
            for s in items
        ]
        return PaginatedSuites(
            total=total, page=query.page, page_size=query.page_size, items=out_items
        )

    @classmethod
    async def _filter_suite_ids_by_last_run_status(
        cls, project_id: int, status: RunStatus
    ) -> list[int]:
        from service.test_execution.models import TestSuiteRun

        suites = await TestSuite.filter(project_id=project_id).values("id")
        suite_ids = [s["id"] for s in suites]
        last_runs = await fetch_suite_last_runs(suite_ids)
        return [sid for sid, run in last_runs.items() if run.status == status]

    @classmethod
    async def create(cls, user: User, data: SuiteCreateRequest) -> SuiteDetailOut:
        cls._reject_ui_not_implemented(data.type)
        await ensure_tm_editor(data.project_id, user)
        await ensure_unique_suite_name(data.project_id, data.suite_name)
        await cls._validate_module(data.project_id, data.module_id)
        await cls._validate_environment(data.project_id, data.environment_id)
        await cls._validate_api_suite_fields(data.project_id, data.type, data.environment_id)
        suite = await TestSuite.create(
            project_id=data.project_id,
            module_id=data.module_id,
            environment_id=data.environment_id,
            suite_name=data.suite_name,
            description=data.description,
            type=data.type,
            run_mode=data.run_mode,
            created_by_id=user.id,
        )
        if data.cases:
            from service.test_management.suite.case_relation_service import CaseRelationService

            await CaseRelationService.replace(user, suite.id, data.cases, skip_permission=True)
        return await cls.get_detail(user, suite.id)

    @classmethod
    async def get_detail(cls, user: User, suite_id: int) -> SuiteDetailOut:
        suite = await cls._get_suite_or_404(suite_id)
        await ensure_tm_viewer(suite.project_id, user)
        case_counts = await count_suite_cases([suite.id])
        last_runs = await fetch_suite_last_runs([suite.id])
        base = cls._to_out(
            suite,
            case_count=case_counts.get(suite.id, 0),
            last_run=LastRunBrief(**last_run_brief_from_suite_run(last_runs.get(suite.id))),
        )
        task_rels = await TaskSuiteRelation.filter(suite_id=suite.id).prefetch_related("task")
        bound_tasks = [
            BoundTaskBrief(id=rel.task.id, task_name=rel.task.task_name) for rel in task_rels
        ]
        return SuiteDetailOut(**base.model_dump(), bound_tasks=bound_tasks)

    @classmethod
    async def update(cls, user: User, suite_id: int, data: SuiteUpdateRequest) -> SuiteDetailOut:
        suite = await cls._get_suite_or_404(suite_id)
        await ensure_tm_editor(suite.project_id, user)
        if data.suite_name is not None:
            await ensure_unique_suite_name(suite.project_id, data.suite_name, exclude_id=suite.id)
            suite.suite_name = data.suite_name
        if data.description is not None:
            suite.description = data.description
        if data.module_id is not None:
            await cls._validate_module(suite.project_id, data.module_id)
            suite.module_id = data.module_id
        if data.environment_id is not None:
            await cls._validate_environment(suite.project_id, data.environment_id)
            suite.environment_id = data.environment_id
        if data.run_mode is not None:
            suite.run_mode = data.run_mode
        await cls._validate_api_suite_fields(suite.project_id, suite.type, suite.environment_id)
        await suite.save()
        return await cls.get_detail(user, suite.id)

    @classmethod
    async def delete(cls, user: User, suite_id: int) -> None:
        suite = await cls._get_suite_or_404(suite_id)
        await ensure_tm_editor(suite.project_id, user)
        from service.test_execution.run.run_lock import assert_no_running_for_suite

        await assert_no_running_for_suite(suite_id)
        await suite.delete()

    @classmethod
    async def batch_delete(cls, user: User, data) -> dict:
        deleted_ids = []
        failures = []
        for item_id in data.suite_ids:
            try:
                await cls.delete(user, item_id)
                deleted_ids.append(item_id)
            except AppException as e:
                failures.append({'suite_id': item_id, 'message': e.message})
            except Exception as e:
                failures.append({'suite_id': item_id, 'message': str(e)})
        return {'deleted_ids': deleted_ids, 'failures': failures}
