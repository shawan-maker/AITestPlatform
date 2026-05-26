from typing import Any

from service.api_test.dependency.schemas import DependencyEdgeDraft


class AiDependencyAnalyzer:
    """Optional LLM-based dependency inference (stub: returns empty when disabled)."""

    CONFIDENCE_THRESHOLD = 0.7

    @classmethod
    async def analyze(
        cls,
        target: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> list[DependencyEdgeDraft]:
        # Phase B: wire to LLM + RAG when configured
        _ = target, candidates
        return []
