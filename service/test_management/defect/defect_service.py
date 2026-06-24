from __future__ import annotations

from service.core.enums import DefectHistoryAction, DefectStatus
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.project.models import Project, ProjectModule
from service.test_execution.models import TestDefect, TestDefectComment, TestDefectHistory
from service.test_management.defect.assignee_validator import ensure_assignee_in_project
from service.test_management.defect.defect_writer import DefectWriter
from service.test_management.defect.history_writer import DefectHistoryWriter
from service.test_management.defect.schemas import (
    DefectCommentCreateRequest,
    DefectCommentOut,
    DefectDetailOut,
    DefectHistoryOut,
    DefectListItemOut,
    DefectListQuery,
    DefectManualCreateRequest,
    DefectSourceOut,
    DefectStatusTimelineItem,
    DefectTransitionRequest,
    DefectUpdateRequest,
    PaginatedDefects,
)
from service.test_management.defect.source_resolver import resolve_source_brief
from service.test_management.defect.transition import validate_transition
from service.test_management.permissions import ensure_tm_editor, ensure_tm_viewer
from service.user.models import User


class DefectService:
    @classmethod
    async def _get_defect_or_404(cls, defect_id: int) -> TestDefect:
        defect = await TestDefect.get_or_none(id=defect_id)
        if defect is None:
            raise AppException("缺陷不存在", 404)
        return defect

    @classmethod
    async def _validate_module(cls, project_id: int, module_id: int | None) -> None:
        if module_id is None:
            return
        if not await ProjectModule.filter(id=module_id, project_id=project_id).exists():
            raise AppException("项目模块不存在", 404)

    @classmethod
    async def _user_names(cls, user_ids: set[int]) -> dict[int, str]:
        if not user_ids:
            return {}
        users = await User.filter(id__in=list(user_ids))
        return {u.id: u.username for u in users}

    @classmethod
    def _list_item(
        cls,
        defect: TestDefect,
        names: dict[int, str],
    ) -> DefectListItemOut:
        return DefectListItemOut(
            id=defect.id,
            defect_code=defect.defect_code,
            title=defect.title,
            severity=defect.severity,
            priority=defect.priority,
            status=defect.status,
            defect_category=defect.defect_category,
            assignee_id=defect.assignee_id,
            assignee_name=names.get(defect.assignee_id) if defect.assignee_id else None,
            created_by_id=defect.created_by_id,
            created_by_name=names.get(defect.created_by_id) if defect.created_by_id else None,
            created_at=defect.created_at,
        )

    @classmethod
    async def list(cls, user: User, query: DefectListQuery) -> PaginatedDefects:
        await ensure_tm_viewer(query.project_id, user)
        qs = TestDefect.filter(project_id=query.project_id)
        if query.id is not None:
            qs = qs.filter(id=query.id)
        if query.q:
            qs = qs.filter(title__icontains=query.q.strip())
        if query.severity is not None:
            qs = qs.filter(severity=query.severity)
        if query.priority is not None:
            qs = qs.filter(priority=query.priority)
        if query.status is not None:
            qs = qs.filter(status=query.status)
        if query.defect_category is not None:
            qs = qs.filter(defect_category=query.defect_category)
        if query.created_by_id is not None:
            qs = qs.filter(created_by_id=query.created_by_id)
        if query.assignee_id is not None:
            qs = qs.filter(assignee_id=query.assignee_id)
        if query.created_from is not None:
            qs = qs.filter(created_at__gte=query.created_from)
        if query.created_to is not None:
            qs = qs.filter(created_at__lte=query.created_to)
        qs = qs.order_by("-created_at", "-id")
        total, items = await paginate(qs, query.page, query.page_size)
        user_ids: set[int] = set()
        for d in items:
            if d.assignee_id:
                user_ids.add(d.assignee_id)
            if d.created_by_id:
                user_ids.add(d.created_by_id)
        names = await cls._user_names(user_ids)
        return PaginatedDefects(
            total=total,
            page=query.page,
            page_size=query.page_size,
            items=[cls._list_item(d, names) for d in items],
        )

    @classmethod
    async def create_manual(cls, user: User, data: DefectManualCreateRequest) -> DefectDetailOut:
        await ensure_tm_editor(data.project_id, user)
        await cls._validate_module(data.project_id, data.module_id)
        defect = await DefectWriter.create_manual(
            user,
            project_id=data.project_id,
            module_id=data.module_id,
            title=data.title,
            defect_category=data.defect_category,
            steps=data.steps,
            severity=data.severity,
            priority=data.priority,
            root_cause=data.root_cause,
            assignee_id=data.assignee_id,
            comment=data.comment,
        )
        return await cls.get_detail(user, defect.id)

    @classmethod
    async def get_detail(cls, user: User, defect_id: int) -> DefectDetailOut:
        defect = await cls._get_defect_or_404(defect_id)
        await ensure_tm_viewer(defect.project_id, user)

        project = await Project.get_or_none(id=defect.project_id)
        module_name: str | None = None
        if defect.module_id:
            mod = await ProjectModule.get_or_none(id=defect.module_id)
            module_name = mod.name if mod else None

        user_ids = {
            uid
            for uid in (defect.assignee_id, defect.created_by_id, defect.updated_by_id)
            if uid
        }
        names = await cls._user_names(user_ids)

        comments = await TestDefectComment.filter(defect_id=defect.id).order_by(
            "created_at", "id"
        )
        for c in comments:
            if c.created_by_id:
                user_ids.add(c.created_by_id)
        if user_ids - set(names.keys()):
            names.update(await cls._user_names(user_ids - set(names.keys())))

        history_rows = await TestDefectHistory.filter(defect_id=defect.id).order_by(
            "created_at", "id"
        )
        for h in history_rows:
            if h.operator_id:
                user_ids.add(h.operator_id)
        if user_ids - set(names.keys()):
            names.update(await cls._user_names(user_ids - set(names.keys())))

        source = await resolve_source_brief(defect)
        status_timeline = [
            DefectStatusTimelineItem(
                status=DefectStatus(h.new_value),
                at=h.created_at,
                operator_id=h.operator_id,
                operator_name=names.get(h.operator_id) if h.operator_id else None,
            )
            for h in history_rows
            if h.action == DefectHistoryAction.status_change and h.new_value
        ]

        return DefectDetailOut(
            id=defect.id,
            defect_code=defect.defect_code,
            project_id=defect.project_id,
            project_name=project.name if project else None,
            module_id=defect.module_id,
            module_name=module_name,
            title=defect.title,
            defect_category=defect.defect_category,
            steps=defect.steps,
            root_cause=defect.root_cause,
            severity=defect.severity,
            priority=defect.priority,
            status=defect.status,
            external_key=defect.external_key,
            assignee_id=defect.assignee_id,
            assignee_name=names.get(defect.assignee_id) if defect.assignee_id else None,
            created_by_id=defect.created_by_id,
            created_by_name=names.get(defect.created_by_id)
            if defect.created_by_id
            else None,
            created_at=defect.created_at,
            updated_at=defect.updated_at,
            source=DefectSourceOut(
                source_type=source.source_type,
                source_run_id=source.source_run_id,
                source_case_id=source.source_case_id,
                case_name=source.case_name,
                run_label=source.run_label,
                source_unreachable=source.source_unreachable,
            ),
            comments=[
                DefectCommentOut(
                    id=c.id,
                    content=c.content,
                    created_by_id=c.created_by_id,
                    created_by_name=names.get(c.created_by_id) if c.created_by_id else None,
                    created_at=c.created_at,
                )
                for c in comments
            ],
            history=[
                DefectHistoryOut(
                    id=h.id,
                    action=h.action,
                    field_name=h.field_name,
                    old_value=h.old_value,
                    new_value=h.new_value,
                    operator_id=h.operator_id,
                    operator_name=names.get(h.operator_id) if h.operator_id else None,
                    created_at=h.created_at,
                )
                for h in history_rows
            ],
            status_timeline=status_timeline,
        )

    @classmethod
    async def update(
        cls, user: User, defect_id: int, data: DefectUpdateRequest
    ) -> DefectDetailOut:
        defect = await cls._get_defect_or_404(defect_id)
        await ensure_tm_editor(defect.project_id, user)

        old_project_id = defect.project_id
        new_project_id = data.project_id if data.project_id is not None else old_project_id
        if new_project_id != old_project_id:
            await ensure_tm_editor(new_project_id, user)

        module_id = (
            data.module_id if data.module_id is not None else defect.module_id
        )
        await cls._validate_module(new_project_id, module_id)

        updates: list[tuple[str, str | None, str | None]] = []
        if data.project_id is not None and data.project_id != defect.project_id:
            updates.append(
                ("project_id", str(defect.project_id), str(data.project_id))
            )
            defect.project_id = data.project_id
        if data.module_id is not None and data.module_id != defect.module_id:
            updates.append(
                ("module_id", str(defect.module_id), str(data.module_id))
            )
            defect.module_id = data.module_id
        if data.title is not None and data.title != defect.title:
            updates.append(("title", defect.title, data.title))
            defect.title = data.title
        if data.defect_category is not None and data.defect_category != defect.defect_category:
            updates.append(
                (
                    "defect_category",
                    defect.defect_category.value,
                    data.defect_category.value,
                )
            )
            defect.defect_category = data.defect_category
        if data.steps is not None and data.steps != defect.steps:
            updates.append(("steps", defect.steps, data.steps))
            defect.steps = data.steps
        if data.severity is not None and data.severity != defect.severity:
            updates.append(
                ("severity", defect.severity.value, data.severity.value)
            )
            defect.severity = data.severity
        if data.priority is not None and data.priority != defect.priority:
            updates.append(
                ("priority", defect.priority.value, data.priority.value)
            )
            defect.priority = data.priority
        if data.root_cause is not None and data.root_cause != defect.root_cause:
            updates.append(("root_cause", defect.root_cause, data.root_cause))
            defect.root_cause = data.root_cause

        if not updates:
            return await cls.get_detail(user, defect_id)

        defect.updated_by_id = user.id
        await defect.save()
        for field_name, old_val, new_val in updates:
            await DefectHistoryWriter.record_field_update(
                defect.id,
                user,
                field_name=field_name,
                old_value=old_val,
                new_value=new_val,
            )
        return await cls.get_detail(user, defect_id)

    @classmethod
    async def transition(
        cls, user: User, defect_id: int, data: DefectTransitionRequest
    ) -> DefectDetailOut:
        defect = await cls._get_defect_or_404(defect_id)
        await ensure_tm_editor(defect.project_id, user)
        validate_transition(defect.status, data.status)

        if data.assignee_id is not None:
            await ensure_assignee_in_project(
                defect.project_id, data.assignee_id, operator=user
            )
            if data.assignee_id != defect.assignee_id:
                old = str(defect.assignee_id) if defect.assignee_id else None
                defect.assignee_id = data.assignee_id
                await DefectHistoryWriter.record_field_update(
                    defect.id,
                    user,
                    field_name="assignee_id",
                    old_value=old,
                    new_value=str(data.assignee_id),
                )

        old_status = defect.status.value
        defect.status = data.status
        defect.updated_by_id = user.id
        await defect.save()
        await DefectHistoryWriter.record_status_change(
            defect.id,
            user,
            old_status=old_status,
            new_status=data.status.value,
        )
        return await cls.get_detail(user, defect_id)

    @classmethod
    async def add_comment(
        cls, user: User, defect_id: int, data: DefectCommentCreateRequest
    ) -> DefectDetailOut:
        defect = await cls._get_defect_or_404(defect_id)
        await ensure_tm_editor(defect.project_id, user)
        comment = await TestDefectComment.create(
            defect_id=defect.id,
            content=data.content.strip(),
            created_by_id=user.id,
        )
        defect.updated_by_id = user.id
        await defect.save(update_fields=["updated_by_id", "updated_at"])
        await DefectHistoryWriter.record_comment_added(
            defect.id, user, comment_id=comment.id
        )
        return await cls.get_detail(user, defect_id)

    @classmethod
    async def delete(cls, user: User, defect_id: int) -> None:
        defect = await TestDefect.get_or_none(id=defect_id)
        if not defect:
            raise AppException("缺陷不存在", 404)
        ensure_tm_editor(defect.project_id, user)
        await TestDefectComment.filter(defect_id=defect_id).delete()
        await TestDefectHistory.filter(defect_id=defect_id).delete()
        await defect.delete()

    @classmethod
    async def batch_delete(cls, user: User, data) -> dict:
        deleted_ids = []
        failures = []
        for item_id in data.defect_ids:
            try:
                await cls.delete(user, item_id)
                deleted_ids.append(item_id)
            except AppException as e:
                failures.append({'defect_id': item_id, 'message': e.message})
            except Exception as e:
                failures.append({'defect_id': item_id, 'message': str(e)})
        return {'deleted_ids': deleted_ids, 'failures': failures}
