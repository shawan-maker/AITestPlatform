"""
Swagger 2.x 接口文档解析：将 swagger.json 转为 APIDocumentParserModel 兼容的字典列表。

模块级函数 ``follow_ref`` / ``resolve_schema`` / ``schema_to_body_fields`` 等亦供
``openapi_document_parser`` 复用（OpenAPI 3.x 的 schema 结构与之兼容）。
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 允许「直接运行本文件」时也能解析 `utils.*`（运行方式：python utils/swagger_document_parser.py）
if __package__ is None:
    _PROJECT_ROOT = Path(__file__).resolve().parents[1]
    _root_s = str(_PROJECT_ROOT)
    if _root_s not in sys.path:
        sys.path.insert(0, _root_s)

from utils.parser.api_document_models import (
    APIDocumentParserModel,
    BodyField,
    Parameter,
    RequestBody,
    Response,
)

logger = logging.getLogger(__name__)

HTTP_METHODS = frozenset(
    {"get", "post", "put", "delete", "patch", "head", "options"}
)


# --- 以下为 schema / 示例 转换公共逻辑（OpenAPI 3 解析器会 import 复用） ---


def follow_ref(spec: Dict[str, Any], ref: str) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        return {}
    parts = ref[2:].split("/")
    cur: Any = spec
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return {}
        cur = cur[part]
    return cur if isinstance(cur, dict) else {}


def resolve_schema(spec: Dict[str, Any], schema: Any) -> Dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    seen: set[str] = set()

    def inner(s: Dict[str, Any]) -> Dict[str, Any]:
        if "$ref" in s:
            ref = s["$ref"]
            if ref in seen:
                return {}
            seen.add(ref)
            resolved = follow_ref(spec, ref)
            merged = inner(resolved)
            copy = {k: v for k, v in s.items() if k != "$ref"}
            return {**merged, **copy}
        out = dict(s)
        if "items" in out and isinstance(out["items"], dict):
            out["items"] = inner(out["items"])
        if "properties" in out and isinstance(out["properties"], dict):
            out["properties"] = {
                k: inner(v) if isinstance(v, dict) else v
                for k, v in out["properties"].items()
            }
        if "allOf" in out and isinstance(out["allOf"], list):
            merged: Dict[str, Any] = {}
            for part in out["allOf"]:
                if isinstance(part, dict):
                    part = inner(part)
                    if part.get("properties"):
                        merged.setdefault("properties", {}).update(part["properties"])
                    if part.get("required"):
                        merged.setdefault("required", []).extend(part["required"])
                    if not merged.get("type") and part.get("type"):
                        merged["type"] = part["type"]
            merged["type"] = merged.get("type") or "object"
            return inner(merged)
        return out

    return inner(schema)


def schema_type_string(schema: Dict[str, Any]) -> str:
    t = schema.get("type")
    if isinstance(t, list) and t:
        t = t[0]
    if not t:
        if schema.get("properties"):
            t = "object"
        elif schema.get("items"):
            t = "array"
        else:
            t = "string"
    fmt = schema.get("format")
    if fmt:
        return f"{t}({fmt})"
    return str(t)


def property_to_body_field(
    name: str,
    prop_schema: Dict[str, Any],
    required_set: set,
    spec: Dict[str, Any],
    force_optional_inner: bool = False,
) -> BodyField:
    s = resolve_schema(spec, prop_schema)
    typ = schema_type_string(s)
    desc = s.get("description") or ""
    if not isinstance(desc, str):
        desc = str(desc)
    required = name in required_set and not force_optional_inner

    nested_fields: Optional[List[Dict[str, Any]]] = None
    array_item_fields: Optional[List[Dict[str, Any]]] = None

    stype = s.get("type")
    if isinstance(stype, list) and stype:
        stype = stype[0]

    if stype == "object" or (stype is None and s.get("properties")):
        typ = "object"
        child_req = set(s.get("required") or [])
        nested_fields = []
        for child_name, child_s in (s.get("properties") or {}).items():
            if isinstance(child_s, dict):
                nested_fields.append(
                    property_to_body_field(
                        child_name, child_s, child_req, spec
                    ).model_dump()
                )
    elif stype == "array":
        typ = "array"
        items = s.get("items") or {}
        if isinstance(items, dict):
            item_bf = property_to_body_field(
                f"{name}_item", items, set(), spec, force_optional_inner=True
            )
            array_item_fields = [item_bf.model_dump()]

    return BodyField(
        name=name,
        type=typ,
        description=desc,
        required=required,
        nested_fields=nested_fields,
        array_item_fields=array_item_fields,
    )


def schema_to_body_fields(
    spec: Dict[str, Any], schema: Dict[str, Any]
) -> List[BodyField]:
    schema = resolve_schema(spec, schema)
    t = schema.get("type")
    if t == "array" and "items" in schema:
        item_schema = schema.get("items") or {}
        item_schema = resolve_schema(
            spec, item_schema if isinstance(item_schema, dict) else {}
        )
        nested = property_to_body_field(
            "items", item_schema, set(), spec, force_optional_inner=True
        )
        return [
            BodyField(
                name="root",
                type="array",
                description="",
                required=True,
                nested_fields=None,
                array_item_fields=[nested.model_dump()],
            )
        ]
    if schema.get("properties") or t == "object" or t is None:
        props = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        fields: List[BodyField] = []
        for pname, sub in props.items():
            if isinstance(sub, dict):
                fields.append(property_to_body_field(pname, sub, required, spec))
        return fields
    return [property_to_body_field("value", schema, {"value"}, spec)]


def example_value_for_schema(spec: Dict[str, Any], schema: Dict[str, Any]) -> Any:
    schema = resolve_schema(spec, schema)
    t = schema.get("type")
    if isinstance(t, list) and t:
        t = t[0]
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if t == "object" or schema.get("properties"):
        return schema_to_example_dict(spec, schema)
    if t == "array":
        it = schema.get("items") or {}
        if isinstance(it, dict):
            return [example_value_for_schema(spec, it)]
        return []
    if t in ("integer", "number"):
        return 0
    if t == "boolean":
        return False
    if t == "string":
        fmt = schema.get("format")
        if fmt == "date":
            return "1970-01-01"
        if fmt == "date-time":
            return "1970-01-01T00:00:00Z"
        return ""
    return None


def schema_to_example_dict(
    spec: Dict[str, Any], schema: Dict[str, Any]
) -> Dict[str, Any]:
    schema = resolve_schema(spec, schema)
    t = schema.get("type")
    if isinstance(t, list) and t:
        t = t[0]

    if "example" in schema:
        ex = schema["example"]
        return ex if isinstance(ex, dict) else {"value": ex}

    if t == "object" or schema.get("properties"):
        obj: Dict[str, Any] = {}
        for key, sub in (schema.get("properties") or {}).items():
            if isinstance(sub, dict):
                obj[key] = example_value_for_schema(spec, sub)
        return obj
    if t == "array":
        items = schema.get("items") or {}
        if isinstance(items, dict):
            return {"items": [example_value_for_schema(spec, items)]}
        return {"items": []}
    return {"value": example_value_for_schema(spec, schema)}


class SwaggerDocumentParser:
    """解析 Swagger 2.x 文档为 ``APIDocumentParserModel`` 列表。"""

    def parse_file(self, path: str | Path, encoding: str = "utf-8") -> List[Dict[str, Any]]:
        p = Path(path)
        return self.parse_raw(p.read_text(encoding=encoding))

    def parse_raw(self, raw: str) -> List[Dict[str, Any]]:
        return self.parse_spec(json.loads(raw))

    def parse_spec(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(spec, dict):
            raise ValueError("文档根节点必须为 JSON 对象")
        ver = spec.get("swagger")
        if ver is None or str(ver)[:2] != "2.":
            raise ValueError(
                "不是 Swagger 2.x 文档（缺少 swagger: 2.0）；请使用 OpenAPIDocumentParser 解析 OpenAPI 3.x"
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

        self._collect_parameters_swagger2(spec, merged, params_bucket)
        request_body = self._request_body_swagger2(spec, merged, operation)
        responses = self._build_responses(spec, operation)

        return APIDocumentParserModel(
            path=path,
            method=method,
            summary=summary,
            parameters=params_bucket,
            requestBody=request_body,
            responses=responses,
        )

    def _collect_parameters_swagger2(
        self,
        spec: Dict[str, Any],
        raw_params: List[Dict[str, Any]],
        bucket: Dict[str, List[Parameter]],
    ) -> None:
        for p in raw_params:
            if not isinstance(p, dict):
                continue
            where = p.get("in")
            if where in ("body", "formData"):
                continue
            if where not in ("header", "path", "query"):
                continue
            bucket[where].append(self._param_from_swagger2(spec, p))

    def _param_from_swagger2(self, spec: Dict[str, Any], p: Dict[str, Any]) -> Parameter:
        name = p.get("name", "")
        schema = p.get("schema")
        if isinstance(schema, dict):
            typ = schema_type_string(resolve_schema(spec, schema))
        else:
            typ = p.get("type") or "string"
            if p.get("format"):
                typ = f"{typ}({p.get('format')})"
        desc = p.get("description") or ""
        if not isinstance(desc, str):
            desc = str(desc)
        return Parameter(
            name=str(name),
            type=str(typ),
            description=desc,
            required=bool(p.get("required", False)),
        )

    def _request_body_swagger2(
        self,
        spec: Dict[str, Any],
        raw_params: List[Dict[str, Any]],
        operation: Dict[str, Any],
    ) -> Optional[RequestBody]:
        body_param = None
        for p in raw_params:
            if isinstance(p, dict) and p.get("in") == "body":
                body_param = p
                break

        consumes = operation.get("consumes") or spec.get("consumes") or []
        content_type = consumes[0] if isinstance(consumes, list) and consumes else "application/json"

        if body_param:
            schema = body_param.get("schema") or {}
            schema = resolve_schema(spec, schema)
            return RequestBody(
                content_type=content_type,
                body=schema_to_body_fields(spec, schema),
            )

        form_fields: List[BodyField] = []
        for p in raw_params:
            if isinstance(p, dict) and p.get("in") == "formData":
                typ = p.get("type") or "string"
                if p.get("format"):
                    typ = f"{typ}({p.get('format')})"
                form_fields.append(
                    BodyField(
                        name=str(p.get("name", "")),
                        type=str(typ),
                        description=str(p.get("description") or ""),
                        required=bool(p.get("required", False)),
                    )
                )
        if not form_fields:
            return None

        ct = "application/x-www-form-urlencoded"
        if isinstance(consumes, list):
            for c in consumes:
                if "multipart" in c:
                    ct = c
                    break
                if "urlencoded" in c:
                    ct = c
        return RequestBody(content_type=ct, body=form_fields)

    def _build_responses(self, spec: Dict[str, Any], operation: Dict[str, Any]) -> List[Response]:
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
            schema = resp.get("schema")
            if isinstance(schema, dict):
                schema = resolve_schema(spec, schema)
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


def parse_swagger_file(path: str | Path, encoding: str = "utf-8") -> List[Dict[str, Any]]:
    """便捷函数：解析 Swagger 2.x 文件。"""
    return SwaggerDocumentParser().parse_file(path, encoding=encoding)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # # 优先：命令行传入 swagger json 路径
    # #   python -m utils.swagger_document_parser path/to/swagger.json
    # #   或：python utils/swagger_document_parser.py path/to/swagger.json
    # if len(sys.argv) >= 2:
    #     out = parse_swagger_file(sys.argv[1])
    #     print(json.dumps(out, ensure_ascii=False, indent=2))
    #     sys.exit(0)

    # 无参数时：若存在默认示例文件则解析，否则提示用法
    _default = Path(__file__).resolve().parents[1] / "test_data" / "swagger_pisces.json"
    if _default.is_file():
        out = parse_swagger_file(_default)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(
            "用法: python -m utils.swagger_document_parser <swagger.json>\n"
            f"或将 swagger 文件放在: {_default}"
        )
        sys.exit(1)