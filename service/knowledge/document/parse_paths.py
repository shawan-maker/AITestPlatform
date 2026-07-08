"""知识库管理模块 - document/parse_paths

parse paths
"""
from pathlib import Path

from service.core.settings import BASE_DIR


def resolve_storage_file_path(relative_path: str | None) -> Path | None:
    """解析知识库上传原件等相对路径（兼容 Windows 反斜杠）。"""
    raw = (relative_path or "").strip()
    if not raw:
        return None

    normalized = raw.replace("\\", "/")
    rel = Path(normalized)
    candidates: list[Path] = []
    if rel.is_absolute():
        candidates.append(rel)
    else:
        candidates.append(Path(BASE_DIR) / rel)
        candidates.append(Path(BASE_DIR) / Path(*normalized.split("/")))

    seen: set[str] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if resolved.is_file():
            return resolved
    return None


def resolve_parse_result_path(parse_result_path: str) -> Path | None:
    raw = parse_result_path.strip()
    if not raw:
        return None

    normalized = raw.replace("\\", "/")
    rel = Path(normalized)
    candidates: list[Path] = []
    if rel.is_absolute():
        candidates.append(rel)
    else:
        candidates.append(Path(BASE_DIR) / rel)
        candidates.append(Path(BASE_DIR) / Path(*normalized.split("/")))

    seen: set[str] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if resolved.is_file():
            return resolved
    return None


def resolve_parse_result_dir(parse_result_path: str) -> Path | None:
    parse_path = resolve_parse_result_path(parse_result_path)
    if parse_path is None:
        raw = parse_result_path.strip().replace("\\", "/")
        if not raw:
            return None
        rel = Path(raw)
        candidates: list[Path] = []
        if rel.is_absolute():
            candidates.append(rel.parent)
        else:
            candidates.append((Path(BASE_DIR) / rel).parent)
            parts = normalized.split("/") if (normalized := raw) else []
            if len(parts) > 1:
                candidates.append(Path(BASE_DIR) / Path(*parts[:-1]))
        for path in candidates:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved.is_dir():
                return resolved
        return None
    return parse_path.parent
