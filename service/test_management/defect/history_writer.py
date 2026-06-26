from service.core.enums import DefectHistoryAction
from service.test_execution.models import TestDefectHistory
from service.user.models import User


class DefectHistoryWriter:
    @classmethod
    async def record_created(cls, defect_id: int, operator: User) -> None:
        await TestDefectHistory.create(
            defect_id=defect_id,
            action=DefectHistoryAction.created,
            operator_id=operator.id,
        )

    @classmethod
    async def record_field_update(
        cls,
        defect_id: int,
        operator: User,
        *,
        field_name: str,
        old_value: str | None,
        new_value: str | None,
    ) -> None:
        if old_value == new_value:
            return
        await TestDefectHistory.create(
            defect_id=defect_id,
            action=DefectHistoryAction.field_update,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            operator_id=operator.id,
        )

    @classmethod
    async def record_status_change(
        cls,
        defect_id: int,
        operator: User,
        *,
        old_status: str,
        new_status: str,
    ) -> None:
        await TestDefectHistory.create(
            defect_id=defect_id,
            action=DefectHistoryAction.status_change,
            field_name="status",
            old_value=old_status,
            new_value=new_status,
            operator_id=operator.id,
        )

    @classmethod
    async def record_comment_added(
        cls,
        defect_id: int,
        operator: User,
        *,
        comment_id: int,
        content: str = "",
    ) -> None:
        await TestDefectHistory.create(
            defect_id=defect_id,
            action=DefectHistoryAction.comment_added,
            field_name="comment",
            old_value=None,
            new_value=content or str(comment_id),
            operator_id=operator.id,
        )
