from datetime import datetime, timezone

from service.core.enums import FunctionalExecResult, RunStatus, TaskSuiteType
from service.core.exceptions import AppException
from service.functional_test.case.models import FunctionalCase
from service.test_execution.manual.schemas import (
    ManualCaseDetailOut,
    ManualCaseUpdateRequest,
    ManualRunContextOut,
    ManualSessionOut,
)
from service.test_execution.models import FunctionalCaseRunRecord, TestTaskRun
from service.test_execution.run.run_lock import get_running_task_run
from service.test_execution.run.schemas import TriggerRunOut
from service.test_execution.shared.summary_calculator import compute_run_status
from service.test_management.models import TaskCaseRelation, TestTask
from service.test_management.permissions import ensure_tm_editor, ensure_tm_viewer
from service.test_management.task.case_relation_service import TaskCaseRelationService
from service.user.models import User


class ManualRunService:
    @classmethod
    async def open_session(cls, user: User, task_id: int) -> ManualSessionOut:
        task = await TestTask.get_or_none(id=task_id)
        if task is None:
            raise AppException("任务不存在", 404)
        if task.type != TaskSuiteType.functional:
            raise AppException("仅功能任务支持手工执行", 400)
        await ensure_tm_editor(task.project_id, user)

        running = await get_running_task_run(task_id)
        if running:
            return ManualSessionOut(
                task_run_id=running.id, status=RunStatus.running, resumed=True
            )

        total_cases = await TaskCaseRelation.filter(task_id=task_id).count()
        task_run = await TestTaskRun.create(
            task_id=task_id,
            triggered_by_id=user.id,
            status=RunStatus.running,
            total_cases=total_cases,
            start_time=datetime.now(timezone.utc),
        )
        return ManualSessionOut(
            task_run_id=task_run.id, status=RunStatus.running, resumed=False
        )

    @classmethod
    async def get_context(cls, user: User, task_run_id: int) -> ManualRunContextOut:
        task_run = await TestTaskRun.get_or_none(id=task_run_id)
        if task_run is None:
            raise AppException("任务运行记录不存在", 404)
        task = await TestTask.get_or_none(id=task_run.task_id)
        if task is None:
            raise AppException("任务不存在", 404)
        await ensure_tm_viewer(task.project_id, user)
        tree = await TaskCaseRelationService.get_tree(user, task.id)
        records = await FunctionalCaseRunRecord.filter(task_run_id=task_run_id)
        record_map = {r.functional_case_id: r for r in records}

        # Batch-resolve module names
        all_module_ids = set()

        def collect_module_ids(nodes):
            for node in nodes:
                for case in node.cases:
                    if case.module_id:
                        all_module_ids.add(case.module_id)
                collect_module_ids(node.children)

        collect_module_ids(tree)
        module_map = {}
        if all_module_ids:
            from service.project.models import ProjectModule
            modules = await ProjectModule.filter(id__in=list(all_module_ids))
            module_map = {m.id: m.name for m in modules}

        # Batch-resolve defect codes for records that have a defect linked
        defect_ids = [r.defect_id for r in records if r.defect_id]
        defect_code_map = {}
        if defect_ids:
            from service.test_execution.models import TestDefect
            defects = await TestDefect.filter(id__in=defect_ids)
            defect_code_map = {d.id: d.defect_code for d in defects}

        # Batch-resolve executor names
        user_ids = [r.triggered_by_id for r in records if r.triggered_by_id]
        user_name_map = {}
        if user_ids:
            users = await User.filter(id__in=list(set(user_ids)))
            user_name_map = {u.id: u.username for u in users}

        def attach_results(nodes):
            for node in nodes:
                for case in node.cases:
                    rec = record_map.get(case.case_id)
                    if rec:
                        case.exec_result = rec.exec_result.value if rec.exec_result else None
                        if rec.defect_id:
                            case.defect_code = defect_code_map.get(rec.defect_id)
                        case.triggered_by_name = user_name_map.get(rec.triggered_by_id)
                        case.exec_time = rec.end_time
                attach_results(node.children)

        attach_results(tree)
        return ManualRunContextOut(
            task_run_id=task_run_id,
            task_name=task.task_name,
            status=task_run.status,
            tree=tree,
            module_map=module_map,
        )

    @classmethod
    async def get_case_detail(cls, user: User, task_run_id: int, case_id: int) -> ManualCaseDetailOut:
        task_run = await TestTaskRun.get_or_none(id=task_run_id)
        if task_run is None:
            raise AppException("任务运行记录不存在", 404)
        task = await TestTask.get_or_none(id=task_run.task_id)
        if task is None:
            raise AppException("任务不存在", 404)
        await ensure_tm_viewer(task.project_id, user)
        case = await FunctionalCase.get_or_none(id=case_id, project_id=task.project_id)
        if case is None:
            raise AppException("用例不存在", 404)
        record = await FunctionalCaseRunRecord.get_or_none(
            task_run_id=task_run_id, functional_case_id=case_id
        )
        triggered_by_name = None
        exec_time = None
        if record:
            exec_time = record.end_time
            if record.triggered_by_id:
                tb_user = await User.get_or_none(id=record.triggered_by_id)
                if tb_user:
                    triggered_by_name = tb_user.username
        return ManualCaseDetailOut(
            case_id=case.id,
            case_name=case.case_name,
            preconditions=case.preconditions,
            test_steps=case.test_steps,
            expected_result=case.expected_result,
            exec_result=record.exec_result if record else None,
            remark=record.remark if record else None,
            record_id=record.id if record else None,
            triggered_by_name=triggered_by_name,
            exec_time=exec_time,
        )

    @classmethod
    async def update_case_result(
        cls, user: User, task_run_id: int, case_id: int, data: ManualCaseUpdateRequest
    ) -> None:
        task_run = await TestTaskRun.get_or_none(id=task_run_id)
        if task_run is None:
            raise AppException("任务运行记录不存在", 404)
        if task_run.status != RunStatus.running:
            raise AppException("执行会话已结束", 400)
        task = await TestTask.get_or_none(id=task_run.task_id)
        if task is None:
            raise AppException("任务不存在", 404)
        await ensure_tm_editor(task.project_id, user)
        linked = await TaskCaseRelation.filter(task_id=task.id, case_id=case_id).exists()
        if not linked:
            raise AppException("用例不属于该任务", 400)

        now = datetime.now(timezone.utc)
        record, created = await FunctionalCaseRunRecord.get_or_create(
            task_run_id=task_run_id,
            functional_case_id=case_id,
            defaults={
                "exec_result": data.exec_result,
                "remark": data.remark,
                "triggered_by_id": user.id,
                "start_time": now,
                "end_time": now,
            },
        )
        if not created:
            record.exec_result = data.exec_result
            record.remark = data.remark
            record.end_time = now
            record.triggered_by_id = user.id
            await record.save()

        await cls._maybe_complete_task_run(task_run_id)

    @classmethod
    async def _maybe_complete_task_run(cls, task_run_id: int) -> None:
        task_run = await TestTaskRun.get(id=task_run_id)
        total = await TaskCaseRelation.filter(task_id=task_run.task_id).count()
        records = await FunctionalCaseRunRecord.filter(task_run_id=task_run_id)
        finished = [r for r in records if r.exec_result != FunctionalExecResult.pending]
        if len(finished) < total:
            return
        passed = sum(1 for r in finished if r.exec_result == FunctionalExecResult.passed)
        failed = sum(1 for r in finished if r.exec_result == FunctionalExecResult.failed)
        blocked = sum(1 for r in finished if r.exec_result == FunctionalExecResult.blocked)
        skipped = sum(1 for r in finished if r.exec_result == FunctionalExecResult.skipped)
        task_run.passed_cases = passed
        task_run.failed_cases = failed + blocked
        task_run.skipped_cases = skipped
        task_run.error_cases = 0
        task_run.status = compute_run_status(
            passed=passed,
            failed=failed + blocked,
            error=0,
            skipped=skipped,
            total=total,
        )
        task_run.end_time = datetime.now(timezone.utc)
        if task_run.start_time:
            task_run.duration_ms = int(
                (task_run.end_time - task_run.start_time).total_seconds() * 1000
            )
        await task_run.save()
