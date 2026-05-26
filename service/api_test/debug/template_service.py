from service.api_test.debug.schemas import DebugRunOut, DebugTemplateOut, DebugTemplateSaveRequest
from service.api_test.interface.interface_service import InterfaceService
from service.api_test.interface.models import ApiInterfaceDebugTemplate
from service.api_test.permissions import ensure_api_editor, ensure_api_viewer
from service.api_test.shared.payload_builder import build_debug_payload_from_interface
from service.api_test.shared.runner_gateway import RunnerGateway
from service.core.exceptions import AppException
from service.test_environment.models import TestEnvironment
from service.user.models import User


class DebugTemplateService:
    @classmethod
    async def get_template(cls, user: User, interface_id: int) -> DebugTemplateOut:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_viewer(iface.project_id, user)
        tpl = await ApiInterfaceDebugTemplate.get_or_none(interface_id=iface.id)
        if tpl is None:
            return DebugTemplateOut(
                interface_id=iface.id,
                payload=None,
                default_file_id=None,
                updated_at=None,
            )
        return DebugTemplateOut(
            interface_id=iface.id,
            payload=tpl.payload,
            default_file_id=tpl.default_file_id,
            updated_at=tpl.updated_at,
        )

    @classmethod
    async def save_template(
        cls, user: User, interface_id: int, data: DebugTemplateSaveRequest
    ) -> DebugTemplateOut:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_editor(iface.project_id, user)
        tpl, _ = await ApiInterfaceDebugTemplate.get_or_create(interface_id=iface.id)
        tpl.payload = data.payload
        tpl.default_file_id = data.default_file_id
        await tpl.save()
        return DebugTemplateOut(
            interface_id=iface.id,
            payload=tpl.payload,
            default_file_id=tpl.default_file_id,
            updated_at=tpl.updated_at,
        )

    @classmethod
    async def fill_from_doc(cls, user: User, interface_id: int) -> DebugTemplateOut:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_editor(iface.project_id, user)
        payload = build_debug_payload_from_interface(iface)
        tpl, _ = await ApiInterfaceDebugTemplate.get_or_create(interface_id=iface.id)
        tpl.payload = payload
        await tpl.save()
        return DebugTemplateOut(
            interface_id=iface.id,
            payload=tpl.payload,
            default_file_id=tpl.default_file_id,
            updated_at=tpl.updated_at,
        )

    @classmethod
    async def debug_run(
        cls,
        user: User,
        interface_id: int,
        *,
        environment_id: int,
        payload: dict | None,
        file_id: int | None,
    ) -> DebugRunOut:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_editor(iface.project_id, user)
        env = await TestEnvironment.get_or_none(
            id=environment_id, project_id=iface.project_id
        )
        if env is None:
            raise AppException("测试环境不存在", 404)
        if payload is None:
            tpl = await ApiInterfaceDebugTemplate.get_or_none(interface_id=iface.id)
            payload = tpl.payload if tpl else build_debug_payload_from_interface(iface)
        if file_id is not None:
            payload = dict(payload or {})
            payload["file_id"] = file_id
        record = await RunnerGateway.run_interface_debug(
            interface=iface,
            environment_id=environment_id,
            payload=payload,
            triggered_by_id=user.id,
        )
        return DebugRunOut(
            run_record_id=record.id,
            status=record.status.value,
            duration_ms=record.duration_ms,
        )
