"""测试管理模块 - defect/defect_writer

数据写入器
"""
from tortoise.transactions import in_transaction

from service.core.enums import DefectSourceType, DefectStatus
from service.test_execution.models import TestDefect, TestDefectComment
from service.test_management.defect.assignee_validator import ensure_assignee_in_project
from service.test_management.defect.history_writer import DefectHistoryWriter
from service.user.models import User


class DefectWriter:
    @classmethod
    async def _create_core(
        cls,
        user: User,
        *,
        project_id: int,
        module_id: int | None,
        title: str,
        defect_category,
        steps: str | None,
        severity,
        priority,
        root_cause: str | None,
        assignee_id: int | None,
        comment: str | None,
        source_type: DefectSourceType,
        source_run_id: int | None = None,
        source_case_id: int | None = None,
        external_key: str | None = None,
    ) -> TestDefect:
        await ensure_assignee_in_project(project_id, assignee_id, operator=user)

        async with in_transaction():
            defect = await TestDefect.create(
                project_id=project_id,
                module_id=module_id,
                title=title,
                defect_category=defect_category,
                steps=steps,
                severity=severity,
                priority=priority,
                root_cause=root_cause,
                status=DefectStatus.init,
                source_type=source_type,
                source_run_id=source_run_id,
                source_case_id=source_case_id,
                external_key=external_key,
                assignee_id=assignee_id,
                created_by_id=user.id,
                updated_by_id=user.id,
            )
            defect.defect_code = f"defect-{defect.id:06d}"
            await defect.save(update_fields=["defect_code"])
            await DefectHistoryWriter.record_created(defect.id, user)
            if comment and comment.strip():
                c = await TestDefectComment.create(
                    defect_id=defect.id,
                    content=comment.strip(),
                    created_by_id=user.id,
                )
                await DefectHistoryWriter.record_comment_added(
                    defect.id, user, comment_id=c.id
                )
        return defect

    @classmethod
    async def create_manual(
        cls,
        user: User,
        *,
        project_id: int,
        module_id: int | None,
        title: str,
        defect_category,
        steps: str | None,
        severity,
        priority,
        root_cause: str | None,
        assignee_id: int | None,
        comment: str | None,
    ) -> TestDefect:
        return await cls._create_core(
            user,
            project_id=project_id,
            module_id=module_id,
            title=title,
            defect_category=defect_category,
            steps=steps,
            severity=severity,
            priority=priority,
            root_cause=root_cause,
            assignee_id=assignee_id,
            comment=comment,
            source_type=DefectSourceType.manual,
        )

    @classmethod
    async def create_from_run(
        cls,
        user: User,
        *,
        project_id: int,
        module_id: int | None,
        title: str,
        defect_category,
        steps: str | None,
        severity,
        priority,
        root_cause: str | None,
        assignee_id: int | None,
        comment: str | None,
        source_type: DefectSourceType,
        source_run_id: int | None,
        source_case_id: int | None,
    ) -> TestDefect:
        return await cls._create_core(
            user,
            project_id=project_id,
            module_id=module_id,
            title=title,
            defect_category=defect_category,
            steps=steps,
            severity=severity,
            priority=priority,
            root_cause=root_cause,
            assignee_id=assignee_id,
            comment=comment,
            source_type=source_type,
            source_run_id=source_run_id,
            source_case_id=source_case_id,
        )

    @classmethod
    async def create_batch_stub(
        cls,
        user: User,
        *,
        project_id: int,
        title: str,
        external_key: str,
    ) -> TestDefect:
        from service.core.enums import DefectCategory, DefectPriority, DefectSeverity

        return await cls._create_core(
            user,
            project_id=project_id,
            module_id=None,
            title=title,
            defect_category=DefectCategory.other,
            steps=None,
            severity=DefectSeverity.normal,
            priority=DefectPriority.medium,
            root_cause=None,
            assignee_id=None,
            comment=None,
            source_type=DefectSourceType.api_case,
            external_key=external_key,
        )
