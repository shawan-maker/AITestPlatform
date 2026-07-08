"""
OpenAPI 3.x 接口文档解析：将 openapi.json 转为 APIDocumentParserModel 兼容的字典列表。

Schema 字段解析与 ``swagger_document_parser`` 中的工具函数复用（同一套 JSON Schema 语义）。
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 允许「直接运行本文件」时也能解析 `utils.*`
if __package__ is None:
    _PROJECT_ROOT = Path(__file__).resolve().parents[1]
    _root_s = str(_PROJECT_ROOT)
    if _root_s not in sys.path:
        sys.path.insert(0, _root_s)

from service.ai_engine.parsers.api_document_models import (
    APIDocumentParserModel,
    Parameter,
    RequestBody,
    Response,
)
from service.ai_engine.parsers.swagger_document_parser import (
    HTTP_METHODS,
    resolve_schema,
    schema_to_body_fields,
    schema_to_example_dict,
    schema_type_string,
)

logger = logging.getLogger(__name__)


def _pick_json_like_content(
    content: Dict[str, Any],
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """从 OpenAPI 3 content 中选取带 schema 的项，优先 application/json 类。"""

    def schema_from(meta: Any) -> Optional[Dict[str, Any]]:
        if isinstance(meta, dict):
            sch = meta.get("schema")
            return sch if isinstance(sch, dict) else None
        return None

    for mt, meta in content.items():
        sch = schema_from(meta)
        if sch is not None and "json" in mt.lower():
            return mt, sch
    for mt, meta in content.items():
        sch = schema_from(meta)
        if sch is not None:
            return mt, sch
    return "application/octet-stream", None


class OpenAPIDocumentParser:
    """解析 OpenAPI 3.x 文档为 ``APIDocumentParserModel`` 列表。"""

    def parse_file(self, path: str | Path, encoding: str = "utf-8") -> List[Dict[str, Any]]:
        p = Path(path)
        return self.parse_raw(p.read_text(encoding=encoding))

    def parse_raw(self, raw: str) -> List[Dict[str, Any]]:
        return self.parse_spec(json.loads(raw))

    def parse_spec(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(spec, dict):
            raise ValueError("文档根节点必须为 JSON 对象")
        ov = spec.get("openapi")
        if ov is None or not str(ov).startswith("3"):
            raise ValueError(
                "不是 OpenAPI 3.x 文档（缺少 openapi: 3.x.x）；请使用 SwaggerDocumentParser 解析 Swagger 2.x"
            )

        results: List[APIDocumentParserModel] = []
        paths = spec.get("paths") or {}
        if not isinstance(paths, dict):
            return []

        for path_item, path_obj in paths.items():
            if not path_item.startswith("/"):
                path_item = "/" + path_item.lstrip("/")
            if not isinstance(path_obj, dict):
                continue

            for method, operation in path_obj.items():
                m = method.lower()
                if m not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                try:
                    results.append(
                        self._operation_to_model(spec, path_item, m.upper(), operation, path_obj)
                    )
                except Exception as e:
                    logger.warning("跳过 %s %s: %s", m.upper(), path_item, e)

        return [x.model_dump() for x in results]

    def parse_spec_as_models(self, spec: Dict[str, Any]) -> List[APIDocumentParserModel]:
        data = self.parse_spec(spec)
        return [APIDocumentParserModel.model_validate(x) for x in data]

    def _operation_to_model(
        self,
        spec: Dict[str, Any],
        path: str,
        method: str,
        operation: Dict[str, Any],
        path_item_obj: Dict[str, Any],
    ) -> APIDocumentParserModel:
        summary = operation.get("summary") or operation.get("operationId") or ""
        if not isinstance(summary, str):
            summary = str(summary)

        params_bucket: Dict[str, List[Parameter]] = {"header": [], "path": [], "query": []}
        merged: List[Dict[str, Any]] = []
        merged.extend(path_item_obj.get("parameters") or [])
        merged.extend(operation.get("parameters") or [])

        self._collect_parameters_oas3(spec, merged, params_bucket)
        request_body = self._request_body_oas3(spec, operation)
        responses = self._build_responses_oas3(spec, operation)

        tags_raw = operation.get("tags") or []
        tags = [str(t) for t in tags_raw if t] if isinstance(tags_raw, list) else []

        return APIDocumentParserModel(
            path=path,
            method=method,
            summary=summary,
            parameters=params_bucket,
            requestBody=request_body,
            responses=responses,
            tags=tags,
        )

    def _collect_parameters_oas3(
        self,
        spec: Dict[str, Any],
        raw_params: List[Dict[str, Any]],
        bucket: Dict[str, List[Parameter]],
    ) -> None:
        for p in raw_params:
            if not isinstance(p, dict):
                continue
            where = p.get("in")
            if where not in ("header", "path", "query"):
                continue
            bucket[where].append(self._param_from_oas3(spec, p))

    def _param_from_oas3(self, spec: Dict[str, Any], p: Dict[str, Any]) -> Parameter:
        name = p.get("name", "")
        schema = resolve_schema(spec, p.get("schema") or {})
        typ = schema_type_string(schema)
        desc = p.get("description") or ""
        if not isinstance(desc, str):
            desc = str(desc)
        # OpenAPI 3.0: example can be at parameter level or schema level
        example = p.get("example")
        if example is None:
            example = schema.get("example")
        if example is None:
            example = schema.get("default")
        return Parameter(
            name=str(name),
            type=str(typ),
            description=desc,
            required=bool(p.get("required", False)),
            example=example,
        )

    def _request_body_oas3(
        self,
        spec: Dict[str, Any],
        operation: Dict[str, Any],
    ) -> Optional[RequestBody]:
        rb = operation.get("requestBody")
        if not isinstance(rb, dict):
            return None
        content = rb.get("content")
        if not isinstance(content, dict) or not content:
            return None

        media_type, schema = _pick_json_like_content(content)
        if schema is None:
            return None

        schema = resolve_schema(spec, schema)
        return RequestBody(
            content_type=media_type,
            body=schema_to_body_fields(spec, schema),
        )

    def _build_responses_oas3(
        self,
        spec: Dict[str, Any],
        operation: Dict[str, Any],
    ) -> List[Response]:
        out: List[Response] = []
        responses = operation.get("responses") or {}
        if not isinstance(responses, dict):
            return out

        for code, resp in responses.items():
            if not isinstance(resp, dict):
                continue
            http_code = str(code)
            desc = resp.get("description") or ""
            if not isinstance(desc, str):
                desc = str(desc)

            media_type = "application/json"
            example_body: Dict[str, Any] = {}

            content = resp.get("content")
            if isinstance(content, dict) and content:
                mt, schema = _pick_json_like_content(content)
                media_type = mt
                if schema:
                    schema = resolve_schema(spec, schema)
                    example_body = schema_to_example_dict(spec, schema)
            elif isinstance(resp.get("schema"), dict):
                schema = resolve_schema(spec, resp["schema"])
                example_body = schema_to_example_dict(spec, schema)

            out.append(
                Response(
                    http_code=http_code,
                    description=desc,
                    media_type=media_type,
                    response_body=example_body,
                )
            )
        return out


def parse_openapi_file(path: str | Path, encoding: str = "utf-8") -> List[Dict[str, Any]]:
    """便捷函数：解析 OpenAPI 3.x 文件。"""
    return OpenAPIDocumentParser().parse_file(path, encoding=encoding)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) >= 2:
        print(json.dumps(parse_openapi_file(sys.argv[1]), ensure_ascii=False, indent=2))
        sys.exit(0)

    _default = Path(__file__).resolve().parents[1] / "test_data" / "openapi.json"
    if _default.is_file():
        print(json.dumps(parse_openapi_file(_default), ensure_ascii=False, indent=2))
    else:
        print(
            "用法: python -m utils.openapi_document_parser <openapi.json>\n"
            f"或将 openapi 文件放在: {_default}"
        )
        sys.exit(1)
