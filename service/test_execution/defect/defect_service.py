from service.core.enums import DefectSourceType, DefectStatus
from service.core.exceptions import AppException
from service.test_execution.defect.schemas import (
    DefectBatchLinkRequest,
    DefectCreateRequest,
    DefectOut,
)
from service.test_execution.models import ApiCaseRunRecord, FunctionalCaseRunRecord, TestDefect
from service.test_management.permissions import ensure_tm_editor
from service.user.models import User


class DefectService:
    @classmethod
    async def create(cls, user: User, data: DefectCreateRequest) -> DefectOut:
        await ensure_tm_editor(data.project_id, user)
        defect = await TestDefect.create(
            project_id=data.project_id,
            module_id=data.module_id,
            title=data.title,
            steps=data.steps,
            severity=data.severity,
            priority=data.priority,
            status=DefectStatus.init,
            source_type=data.source_type,
            source_run_id=data.source_run_id,
            source_case_id=data.source_case_id,
            created_by_id=user.id,
        )
        if data.case_run_id:
            record = await ApiCaseRunRecord.get_or_none(id=data.case_run_id)
            if record is None:
                raise AppException("API 用例运行记录不存在", 404)
            record.defect_id = defect.id
            await record.save(update_fields=["defect_id"])
        if data.functional_run_id:
            frecord = await FunctionalCaseRunRecord.get_or_none(id=data.functional_run_id)
            if frecord is None:
                raise AppException("功能用例运行记录不存在", 404)
            frecord.defect_id = defect.id
            await frecord.save(update_fields=["defect_id"])
        return DefectOut(
            id=defect.id,
            title=defect.title,
            severity=defect.severity,
            priority=defect.priority,
            status=defect.status,
            external_key=defect.external_key,
        )

    @classmethod
    async def batch_link(cls, user: User, data: DefectBatchLinkRequest) -> dict:
        if not data.external_key and not data.defect_id:
            raise AppException("external_key 与 defect_id 至少提供一个", 400)
        if data.external_key and data.defect_id:
            raise AppException("external_key 与 defect_id 不能同时提供", 400)

        records = await ApiCaseRunRecord.filter(id__in=data.case_run_ids)
        if len(records) != len(set(data.case_run_ids)):
            raise AppException("部分用例运行记录不存在", 404)

        project_ids: set[int] = set()
        for record in records:
            if record.api_case_id:
                from service.api_test.models import ApiTestCase

                case = await ApiTestCase.get_or_none(id=record.api_case_id)
                if case:
                    project_ids.add(case.project_id)
        if len(project_ids) != 1:
            raise AppException("运行记录须属于同一项目", 400)
        project_id = next(iter(project_ids))
        await ensure_tm_editor(project_id, user)

        if data.defect_id:
            defect = await TestDefect.get_or_none(id=data.defect_id, project_id=project_id)
            if defect is None:
                raise AppException("缺陷不存在", 404)
        else:
            defect = await TestDefect.filter(
                project_id=project_id, external_key=data.external_key
            ).first()
            if defect is None:
                defect = await TestDefect.create(
                    project_id=project_id,
                    title=data.external_key or "批量关联缺陷",
                    source_type=DefectSourceType.api_case,
                    external_key=data.external_key,
                    created_by_id=user.id,
                )

        linked = 0
        for record in records:
            record.defect_id = defect.id
            await record.save(update_fields=["defect_id"])
            linked += 1
        return {"defect_id": defect.id, "linked_count": linked}
