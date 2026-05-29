#!/usr/bin/env python3
"""Merge SIT optimization implementation docs into canonical design docs."""
from __future__ import annotations

import glob
import os
import re

BASE = os.path.join(os.path.dirname(__file__), "..", "service", "design")
BASE = os.path.normpath(BASE)


def find_one(pattern: str) -> str:
    hits = glob.glob(os.path.join(BASE, "**", pattern), recursive=True)
    if not hits:
        raise FileNotFoundError(f"No match for {pattern!r} under {BASE}")
    hits.sort(key=len)
    return hits[0]


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content.rstrip() + "\n")


SIT_SECTION = """

---

## SIT 联调优化（已并入本文）

> **来源**：SIT 联调阶段需求（见 [`SIT/`](../SIT/) 目录）  
> **说明**：原独立「SIT 优化实现方案」已合并至本文，后续仅维护本文件。

"""

MERGES = [
    ("04-02-*SIT*.md", "04-02-*用户管理模块实现*.md"),
    ("05-02-*SIT*.md", "05-02-*项目管理模块实现*.md"),
    ("06-01-*SIT*.md", "06-02-*环境管理模块实现*.md"),
    ("17-01-*SIT*.md", "17-01-*项目管理与用户管理前端实现*.md"),
    ("19-01-*SIT*.md", "19-01-*环境管理四模块前端实现*.md"),
]

REF_REPLACEMENTS = [
    ("../backend/04-02-用户管理模块SIT优化实现方案.md", "../backend/04-02-用户管理模块实现_8e998c54.plan.md"),
    ("../backend/05-02-项目管理模块SIT优化实现方案.md", "../backend/05-02-项目管理模块实现_464f05d6.plan.md"),
    ("../backend/06-01-环境变量模块SIT优化实现方案.md", "../backend/06-02-环境管理模块实现_4731549d.plan.md"),
    ("[`04-02-SIT`](../backend/04-02-用户管理模块SIT优化实现方案.md)", "[`04-02`](../backend/04-02-用户管理模块实现_8e998c54.plan.md)"),
    ("[`05-02-SIT`](../backend/05-02-项目管理模块SIT优化实现方案.md)", "[`05-02`](../backend/05-02-项目管理模块实现_464f05d6.plan.md)"),
    ("[`17-01-SIT`](../frontend/17-01-项目管理与用户管理SIT优化实现方案.md)", "[`17-01`](../frontend/17-01-项目管理与用户管理前端实现方案.md)"),
    ("[`06-01-SIT`](../backend/06-01-环境变量模块SIT优化实现方案.md)", "[`06-02`](../backend/06-02-环境管理模块实现_4731549d.plan.md)"),
    ("[`19-01-SIT`](19-01-环境变量管理SIT优化实现方案.md)", "[`19-01`](19-01-环境管理四模块前端实现方案.md)"),
    ("19-01-环境变量管理SIT优化实现方案.md", "19-01-环境管理四模块前端实现方案.md"),
    ("17-01-项目管理与用户管理SIT优化实现方案.md", "17-01-项目管理与用户管理前端实现方案.md"),
    ("04-02-SIT", "04-02"),
    ("05-02-SIT", "05-02"),
    ("06-01-SIT", "06-02"),
    ("17-01-SIT", "17-01"),
    ("19-01-SIT", "19-01"),
]


def strip_sit_header(body: str) -> str:
    if body.startswith("#") and "\n---\n" in body:
        return body.split("\n---\n", 1)[1].lstrip()
    return body


def merge_sit_into_target(sit_path: str, target_path: str) -> None:
    sit_content = strip_sit_header(read(sit_path))
    target_body = read(target_path)

    if "## SIT 联调优化（已并入本文）" in target_body:
        target_body = re.sub(
            r"\n---\n\n## SIT 联调优化（已并入本文）[\s\S]*$",
            "",
            target_body.rstrip(),
        )

    new_target = target_body.rstrip() + SIT_SECTION + sit_content
    write(target_path, new_target)
    os.remove(sit_path)


def patch_refs(content: str) -> str:
    for old, new in REF_REPLACEMENTS:
        content = content.replace(old, new)
    # generic leftover *SIT优化实现方案 links
    content = re.sub(
        r"\[`(\d{2}-\d{2})-SIT`\]\([^)]*SIT[^)]*\.md\)",
        r"[`\1`](\1)",
        content,
    )
    content = content.replace("（**以此为准**）", "")
    content = content.replace("，**以此为准**", "")
    return content


def patch_file(rel_glob: str) -> None:
    for path in glob.glob(os.path.join(BASE, "**", rel_glob), recursive=True):
        if "SIT优化" in path or path.endswith("merge_sit_docs.py"):
            continue
        write(path, patch_refs(read(path)))


def main() -> None:
    deleted: list[str] = []
    merged: list[tuple[str, str]] = []

    for sit_pat, target_pat in MERGES:
        sit_path = find_one(sit_pat)
        target_path = find_one(target_pat)
        merge_sit_into_target(sit_path, target_path)
        deleted.append(os.path.relpath(sit_path, BASE))
        merged.append((os.path.relpath(sit_path, BASE), os.path.relpath(target_path, BASE)))

    # patch cross-references in SIT + overall + related docs
    for pattern in [
        "SIT/*.md",
        "0*.md",
        "backend/04-*.md",
        "backend/05-*.md",
        "backend/06-*.md",
        "frontend/17-*.md",
        "frontend/19-*.md",
    ]:
        patch_file(pattern)

    print("Merged:")
    for src, dst in merged:
        print(f"  {src} -> {dst}")
    print("Deleted:")
    for d in deleted:
        print(f"  {d}")


if __name__ == "__main__":
    main()
