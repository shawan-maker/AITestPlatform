"""Sandbox execution for function file debug."""

from __future__ import annotations

import ast
import builtins
import inspect
import io
import json
import re
import time
import types
import typing
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

VAR_REF_PATTERN = re.compile(r"\$([a-zA-Z_][a-zA-Z0-9_]*)")
METHOD_DEF_PATTERN = re.compile(
    r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", re.MULTILINE
)


def parse_method_names(source_code: str) -> list[str]:
    if not source_code:
        return []
    return METHOD_DEF_PATTERN.findall(source_code)


def method_name_matches(source_code: str, needle: str) -> bool:
    if not needle:
        return True
    key = needle.strip().lower()
    if not key:
        return True
    return any(key in name.lower() for name in parse_method_names(source_code))

DANGEROUS_IMPORTS = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "shutil",
        "pathlib",
        "urllib",
        "http",
        "ftplib",
        "pickle",
        "importlib",
        "ctypes",
        "multiprocessing",
    }
)

_REAL_IMPORT = builtins.__import__


def _safe_import(
    name: str,
    globals: dict | None = None,
    locals: dict | None = None,
    fromlist: tuple = (),
    level: int = 0,
):
    if level != 0:
        raise ImportError("禁止相对导入")
    top_level = name.split(".")[0]
    if top_level in DANGEROUS_IMPORTS:
        raise ImportError(f"禁止导入模块: {top_level}")
    return _REAL_IMPORT(name, globals, locals, fromlist, level)


SAFE_BUILTINS: dict[str, Any] = {
    "__import__": _safe_import,
    "True": True,
    "False": False,
    "None": None,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "len": len,
    "range": range,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "round": round,
    "sorted": sorted,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "isinstance": isinstance,
    "print": print,
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "ImportError": ImportError,
    "AttributeError": AttributeError,
}


def source_has_var_refs(source: str) -> bool:
    return bool(VAR_REF_PATTERN.search(source))


def params_have_var_refs(params: dict[str, Any]) -> bool:
    for value in params.values():
        if isinstance(value, str) and value.startswith("$") and len(value) > 1:
            return True
    return False


def resolve_var_name(value: str) -> str:
    return value[1:] if value.startswith("$") else value


def check_dangerous_imports(source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in DANGEROUS_IMPORTS:
                    raise ValueError(f"禁止导入模块: {mod}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module.split(".")[0]
            if mod in DANGEROUS_IMPORTS:
                raise ValueError(f"禁止导入模块: {mod}")


def parse_literal_value(raw: Any) -> Any:
    if not isinstance(raw, str):
        return raw
    trimmed = raw.strip()
    if trimmed.startswith("$") and len(trimmed) > 1:
        return trimmed
    if trimmed == "":
        return ""
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        return raw


def _unwrap_optional(annotation: Any) -> Any:
    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        args = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def coerce_param_value(value: Any, annotation: Any) -> Any:
    if annotation is inspect.Parameter.empty:
        return parse_literal_value(value) if isinstance(value, str) else value

    annotation = _unwrap_optional(annotation)

    if annotation is int:
        if isinstance(value, bool):
            raise TypeError("无法将 bool 转为 int")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            parsed = parse_literal_value(value)
            if isinstance(parsed, bool):
                raise TypeError("无法将 bool 转为 int")
            return int(parsed)
        return int(value)

    if annotation is float:
        if isinstance(value, bool):
            raise TypeError("无法将 bool 转为 float")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            parsed = parse_literal_value(value)
            if isinstance(parsed, bool):
                raise TypeError("无法将 bool 转为 float")
            return float(parsed)
        return float(value)

    if annotation is bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            parsed = parse_literal_value(value)
            if isinstance(parsed, bool):
                return parsed
            raise TypeError(f"无法将 {value!r} 转为 bool")
        raise TypeError(f"无法将 {type(value).__name__} 转为 bool")

    if annotation is str:
        if value is None:
            return ""
        return str(value)

    return parse_literal_value(value) if isinstance(value, str) else value


def prepare_call_params(
    func: Any, raw_params: dict[str, Any], envs: dict[str, str]
) -> dict[str, Any]:
    resolved = resolve_params(raw_params, envs)
    sig = inspect.signature(func)
    call_kwargs: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if name in resolved:
            call_kwargs[name] = coerce_param_value(resolved[name], param.annotation)
        elif param.default is not inspect.Parameter.empty:
            continue
        else:
            raise TypeError(f"缺少参数: {name}")
    return call_kwargs


def resolve_params(params: dict[str, Any], envs: dict[str, str]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str) and value.startswith("$") and len(value) > 1:
            var_name = resolve_var_name(value)
            if var_name not in envs:
                raise ValueError(f"变量未取到值: {var_name}")
            resolved[key] = envs[var_name]
        else:
            resolved[key] = parse_literal_value(value) if isinstance(value, str) else value
    return resolved


def _build_sandbox_globals(file_name: str, envs: dict[str, str]) -> dict[str, Any]:
    module_name = file_name.removesuffix(".py") if file_name.endswith(".py") else file_name
    return {
        "__builtins__": SAFE_BUILTINS,
        "__name__": module_name or "__sandbox__",
        "__doc__": None,
        "__package__": None,
        "__file__": file_name,
        "ENV": {"envs": envs},
    }


def execute_function(
    source_code: str,
    file_name: str,
    method_name: str,
    params: dict[str, Any],
    envs: dict[str, str],
    *,
    timeout_sec: float = 5.0,
) -> tuple[Any, str, str, int]:
    check_dangerous_imports(source_code)
    compile(source_code, file_name, "exec")

    sandbox_globals = _build_sandbox_globals(file_name, envs)
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    def _run() -> Any:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            exec(compile(source_code, file_name, "exec"), sandbox_globals)
            func = sandbox_globals.get(method_name)
            if func is None or not callable(func):
                raise AttributeError(f"方法 {method_name} 不存在或不可调用")
            call_kwargs = prepare_call_params(func, params, envs)
            return func(**call_kwargs)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run)
        try:
            result = future.result(timeout=timeout_sec)
        except FuturesTimeoutError as exc:
            raise TimeoutError(f"执行超时（{timeout_sec}s）") from exc
    duration_ms = int((time.perf_counter() - started) * 1000)
    return result, stdout_buf.getvalue(), stderr_buf.getvalue(), duration_ms
