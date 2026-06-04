from pathlib import Path

from service.knowledge.document.parse_paths import resolve_parse_result_dir

_MARKER_NAME = ".interfaces_imported"


def import_marker_path(parse_result_path: str) -> Path | None:
    parent = resolve_parse_result_dir(parse_result_path)
    if parent is None:
        return None
    return parent / _MARKER_NAME


def mark_interfaces_imported(parse_result_path: str | None) -> None:
    if not parse_result_path:
        return
    marker = import_marker_path(parse_result_path)
    if marker is None:
        return
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


def is_interfaces_imported(parse_result_path: str | None) -> bool:
    if not parse_result_path:
        return False
    marker = import_marker_path(parse_result_path)
    return marker is not None and marker.is_file()
