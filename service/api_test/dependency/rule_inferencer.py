import re
from typing import Any

from service.api_test.dependency.schemas import DependencyEdgeDraft


_AUTH_PATH_RE = re.compile(r"(login|auth|token|signin|sign-in)", re.I)
_TOKEN_FIELD_RE = re.compile(r"token|access_token|authorization", re.I)


class RuleInferencer:
    """OpenAPI/Swagger heuristic dependency inference."""

    @classmethod
    def infer_for_target(
        cls,
        target: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> list[DependencyEdgeDraft]:
        if cls._is_auth_provider(target):
            return []
        if not cls._is_protected(target):
            return []

        auth_chain = cls._find_auth_chain(candidates)
        if not auth_chain:
            return []

        edges: list[DependencyEdgeDraft] = []
        for idx, provider in enumerate(auth_chain, start=1):
            param_map = None
            if idx == len(auth_chain):
                param_map = cls._build_param_map(provider, target)
            edges.append(
                DependencyEdgeDraft(
                    to_method=provider["method"],
                    to_path=provider["path"],
                    seq=idx,
                    param_map=param_map,
                )
            )
        return edges

    @classmethod
    def infer_batch(
        cls,
        targets: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
    ) -> dict[str, list[DependencyEdgeDraft]]:
        result: dict[str, list[DependencyEdgeDraft]] = {}
        for target in targets:
            key = f"{target['method']}:{target['path']}"
            result[key] = cls.infer_for_target(target, candidates)
        return result

    @staticmethod
    def _is_auth_provider(item: dict[str, Any]) -> bool:
        path = item.get("path") or ""
        if _AUTH_PATH_RE.search(path):
            return True
        responses = item.get("responses") or []
        for resp in responses:
            body = str(resp)
            if _TOKEN_FIELD_RE.search(body):
                return True
        return False

    @staticmethod
    def _is_protected(item: dict[str, Any]) -> bool:
        params = item.get("parameters") or {}
        headers = params.get("header") or []
        for h in headers:
            name = (h.get("name") or "").lower()
            if name in ("authorization", "x-auth-token", "x-access-token"):
                return True
        responses = item.get("responses") or []
        for resp in responses:
            code = str(resp.get("code") if isinstance(resp, dict) else "")
            if code in ("401", "403"):
                return True
        return False

    @classmethod
    def _find_auth_chain(cls, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        providers = [c for c in candidates if cls._is_auth_provider(c)]
        providers.sort(key=lambda x: (x.get("path") or ""))
        return providers[:2]

    @staticmethod
    def _build_param_map(provider: dict[str, Any], target: dict[str, Any]) -> dict[str, str]:
        token_field = "responses.data.token"
        responses = provider.get("responses") or []
        for resp in responses:
            if isinstance(resp, dict):
                body = str(resp.get("body") or resp)
                if "access_token" in body:
                    token_field = "responses.data.access_token"
                    break
        return {"headers.Authorization": token_field}
