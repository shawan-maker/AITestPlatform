import csv
import io

from service.functional_test.case.catalog_service import CatalogService
from service.functional_test.case.models import FunctionalCase
from service.functional_test.permissions import ensure_case_viewer
from service.user.models import User

_EXPORT_COLUMNS = [
    "id",
    "case_no",
    "case_name",
    "catalog_name",
    "priority",
    "dimension",
    "type",
    "status",
    "exec_result",
    "source",
    "preconditions",
    "test_steps",
    "test_data",
    "expected_result",
    "jira_issue_key",
]


class ExportService:
    @classmethod
    async def export_csv(
        cls,
        user: User,
        project_id: int,
        catalog_id: int | None,
    ) -> tuple[str, bytes]:
        await ensure_case_viewer(project_id, user)
        qs = FunctionalCase.filter(project_id=project_id)
        catalog_ids = await CatalogService.collect_catalog_ids_with_descendants(
            project_id, catalog_id
        )
        if catalog_ids is not None:
            qs = qs.filter(catalog_id__in=catalog_ids)
        cases = await qs.order_by("sort_order", "id").prefetch_related("catalog")

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=_EXPORT_COLUMNS)
        writer.writeheader()
        for case in cases:
            writer.writerow(
                {
                    "id": case.id,
                    "case_no": case.case_no or "",
                    "case_name": case.case_name,
                    "catalog_name": case.catalog.name if case.catalog else "",
                    "priority": case.priority,
                    "dimension": case.dimension or "",
                    "type": case.type.value,
                    "status": case.status.value,
                    "exec_result": case.exec_result.value,
                    "source": case.source.value,
                    "preconditions": case.preconditions or "",
                    "test_steps": case.test_steps or "",
                    "test_data": case.test_data or "",
                    "expected_result": case.expected_result or "",
                    "jira_issue_key": case.jira_issue_key or "",
                }
            )

        filename = f"functional_cases_{project_id}.csv"
        content = buffer.getvalue().encode("utf-8-sig")
        return filename, content
