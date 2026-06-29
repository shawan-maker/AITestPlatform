from service.core.enums import DefectCategory, DefectSourceType
from service.core.exceptions import AppException
from service.test_execution.defect.schemas import (
    DefectBatchLinkRequest,
    DefectCreateRequest,
    DefectOut,
)
from service.test_execution.models import ApiCaseRunRecord, FunctionalCaseRunRecord, TestDefect
from service.test_management.defect.category_mapper import (
    infer_category_from_api_case,
    infer_category_from_functional,
)
from service.test_management.defect.defect_writer import DefectWriter
from service.test_management.permissions import ensure_tm_editor
from service.user.models import User


class RunDefectService:
    @classmethod
    async def _infer_category(cls, data: DefectCreateRequest) -> DefectCategory:
        if data.source_type == DefectSourceType.functional_case and data.source_case_id:
            from service.functional_test.case.models import FunctionalCase

            case = await FunctionalCase.get_or_none(id=data.source_case_id)
            if case:
                test_point_type: str | None = None
                if case.test_point_id:
                    await case.fetch_related("test_point")
                    if case.test_point:
                        test_point_type = case.test_point.type
                return infer_category_from_functional(
                    test_point_type=test_point_type,
                    dimension=case.dimension,
                    case_category=case.case_category,
                )
        if data.source_type == DefectSourceType.api_case:
            return infer_category_from_api_case()
        return DefectCategory.other

    @classmethod
    async def _resolve_module_id(
        cls, data: DefectCreateRequest, project_id: int
    ) -> int | None:
        if data.module_id is not None:
            return data.module_id
        if data.source_case_id and data.source_type == DefectSourceType.functional_case:
            from service.functional_test.case.models import FunctionalCase

            case = await FunctionalCase.get_or_none(id=data.source_case_id)
            if case and case.project_id == project_id:
                return case.module_id
        if data.source_case_id and data.source_type == DefectSourceType.api_case:
            from service.api_test.models import ApiTestCase

            case = await ApiTestCase.get_or_none(id=data.source_case_id)
            if case and case.project_id == project_id:
                return case.module_id
        return None

    @classmethod
    async def _link_run_records(
        cls, defect_id: int, data: DefectCreateRequest
    ) -> None:
        if data.case_run_id:
            record = await ApiCaseRunRecord.get_or_none(id=data.case_run_id)
            if record is None:
                raise AppException("API 用例运行记录不存在", 404)
            record.defect_id = defect_id
            await record.save(update_fields=["defect_id"])
        if data.functional_run_id:
            frecord = await FunctionalCaseRunRecord.get_or_none(
                id=data.functional_run_id
            )
            if frecord is None:
                raise AppException("功能用例运行记录不存在", 404)
            frecord.defect_id = defect_id
            await frecord.save(update_fields=["defect_id"])

    @classmethod
    async def create(cls, user: User, data: DefectCreateRequest) -> DefectOut:
        # Resolve project_id from run records if not provided
        project_id = data.project_id
        if project_id is None:
            if data.case_run_id:
                record = await ApiCaseRunRecord.get_or_none(id=data.case_run_id)
                if record and record.api_case_id:
                    from service.api_test.models import ApiTestCase
                    case = await ApiTestCase.get_or_none(id=record.api_case_id)
                    if case:
                        project_id = case.project_id
            if project_id is None and data.functional_run_id:
                frecord = await FunctionalCaseRunRecord.get_or_none(id=data.functional_run_id)
                if frecord:
                    await frecord.fetch_related("functional_case")
                    if frecord.functional_case:
                        project_id = frecord.functional_case.project_id
            if project_id is None:
                raise AppException("无法确定项目，请提供 project_id", 400)
        await ensure_tm_editor(project_id, user)
        defect_category = data.defect_category or await cls._infer_category(data)
        module_id = await cls._resolve_module_id(data, project_id)

        defect = await DefectWriter.create_from_run(
            user,
            project_id=project_id,
            module_id=module_id,
            title=data.title,
            defect_category=defect_category,
            steps=data.steps,
            severity=data.severity,
            priority=data.priority,
            root_cause=data.root_cause,
            assignee_id=data.assignee_id,
            comment=data.comment,
            source_type=data.source_type,
            source_run_id=data.source_run_id,
            source_case_id=data.source_case_id,
        )
        await cls._link_run_records(defect.id, data)
        return DefectOut(
            id=defect.id,
            title=defect.title,
            severity=defect.severity,
            priority=defect.priority,
            status=defect.status,
            defect_category=defect.defect_category,
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
                defect = await DefectWriter.create_batch_stub(
                    user,
                    project_id=project_id,
                    title=data.external_key or "批量关联缺陷",
                    external_key=data.external_key or "",
                )

        linked = 0
        for record in records:
            record.defect_id = defect.id
            await record.save(update_fields=["defect_id"])
            linked += 1
        return {"defect_id": defect.id, "linked_count": linked}


# 兼容旧引用
DefectService = RunDefectService
