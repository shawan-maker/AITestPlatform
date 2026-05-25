from service.core.exceptions import AppException
from service.test_environment.models import DebugRuntimeVar, TestEnvironment
from service.test_environment.permissions import ensure_project_editor, ensure_project_viewer
from service.test_environment.variable.schemas import (
    DebugVarBatchUpsertRequest,
    DebugVarOut,
)
from service.user.models import User


class DebugRuntimeVarService:
    @classmethod
    async def list_vars(cls, user: User, environment_id: int) -> list[DebugVarOut]:
        env = await TestEnvironment.get_or_none(id=environment_id)
        if env is None:
            raise AppException("变量文件不存在", 404)
        await ensure_project_viewer(env.project_id, user)
        vars_ = await DebugRuntimeVar.filter(environment_id=environment_id).order_by("var_key")
        return [cls._to_out(v) for v in vars_]

    @classmethod
    async def batch_upsert(
        cls, user: User, environment_id: int, data: DebugVarBatchUpsertRequest
    ) -> list[DebugVarOut]:
        env = await TestEnvironment.get_or_none(id=environment_id)
        if env is None:
            raise AppException("变量文件不存在", 404)
        await ensure_project_editor(env.project_id, user)
        results = []
        for item in data.items:
            var, _ = await DebugRuntimeVar.update_or_create(
                environment_id=environment_id,
                var_key=item.var_key,
                defaults={
                    "var_value": item.var_value,
                    "source": item.source,
                    "updated_by_id": user.id,
                },
            )
            results.append(cls._to_out(var))
        return results

    @classmethod
    async def delete_var(cls, user: User, var_id: int) -> None:
        var = await DebugRuntimeVar.get_or_none(id=var_id)
        if var is None:
            raise AppException("调试变量不存在", 404)
        env = await TestEnvironment.get(id=var.environment_id)
        await ensure_project_editor(env.project_id, user)
        await var.delete()

    @staticmethod
    def _to_out(var: DebugRuntimeVar) -> DebugVarOut:
        return DebugVarOut(
            id=var.id,
            environment_id=var.environment_id,
            var_key=var.var_key,
            var_value=var.var_value,
            source=var.source,
            updated_by_id=var.updated_by_id,
            updated_at=var.updated_at,
        )
