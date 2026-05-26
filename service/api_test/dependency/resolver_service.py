from service.api_test.dependency.schemas import DependencyResolveResult
from service.api_test.interface.models import ApiInterface
from service.api_test.models import ApiDependency, ApiDependencyGroup
from service.api_test.shared.interface_doc import interface_to_doc_dict
from service.core.exceptions import AppException


class DependencyResolverService:
    @classmethod
    async def resolve(cls, target_interface_id: int) -> DependencyResolveResult:
        target = await ApiInterface.get_or_none(id=target_interface_id, is_current=True)
        if target is None:
            raise AppException("接口不存在", 404)

        group = await ApiDependencyGroup.get_or_none(target_api_id=target.id)
        if group is None:
            return DependencyResolveResult()

        deps = (
            await ApiDependency.filter(dependency_group_id=group.id)
            .order_by("seq")
            .prefetch_related("to_api")
        )
        ordered = [d.to_api for d in deps if d.to_api_id]
        summaries = [
            f"{api.method} {api.path}" + (f" — {api.summary}" if api.summary else "")
            for api in ordered
        ]
        docs = [interface_to_doc_dict(api) for api in ordered]
        param_maps = [d.param_map for d in deps]
        return DependencyResolveResult(
            ordered_to_apis=ordered,
            precoditions_summaries=summaries,
            precoditions_api_doc=docs,
            param_maps=param_maps,
            dependency_group_id=group.id,
        )
