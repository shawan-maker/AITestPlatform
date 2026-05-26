from service.api_test.interface.models import ApiInterface
from service.core.exceptions import AppException


class VersionService:
    @classmethod
    async def ensure_unique_current_path(
        cls,
        project_id: int,
        method: str,
        path: str,
        exclude_id: int | None = None,
    ) -> None:
        qs = ApiInterface.filter(
            project_id=project_id,
            method=method.upper(),
            path=path,
            is_current=True,
        )
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        if await qs.exists():
            raise AppException("当前项目中已存在相同 method+path 的接口", 409)

    @classmethod
    async def bump_version_on_identity_change(
        cls,
        iface: ApiInterface,
        *,
        method: str,
        path: str,
        user_id: int | None,
        updates: dict,
    ) -> ApiInterface:
        method = method.upper()
        if iface.method == method and iface.path == path:
            for key, value in updates.items():
                setattr(iface, key, value)
            iface.updated_by_id = user_id
            await iface.save()
            return iface

        await cls.ensure_unique_current_path(
            iface.project_id, method, path, exclude_id=iface.id
        )
        iface.is_current = False
        iface.updated_by_id = user_id
        await iface.save()

        new_iface = await ApiInterface.create(
            project_id=iface.project_id,
            module_id=updates.get("module_id", iface.module_id),
            catalog_id=updates.get("catalog_id", iface.catalog_id),
            method=method,
            path=path,
            summary=updates.get("summary", iface.summary),
            parameters=updates.get("parameters", iface.parameters),
            request_body=updates.get("request_body", iface.request_body),
            responses=updates.get("responses", iface.responses),
            source=iface.source,
            source_document_id=iface.source_document_id,
            source_document_version_id=iface.source_document_version_id,
            version=iface.version + 1,
            is_current=True,
            sort_order=iface.sort_order,
            created_by_id=user_id,
            updated_by_id=user_id,
        )
        iface.replaced_by_id = new_iface.id
        await iface.save(update_fields=["is_current", "replaced_by_id", "updated_by_id", "updated_at"])
        return new_iface
