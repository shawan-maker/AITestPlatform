"""接口名称翻译工具 — 构建中文→英文翻译映射。

用于英文模式下将接口 summary（中文）翻译为英文，
使 LLM 生成的用例标题和依赖名称为英文，同时保持
DB 查询通过反向映射（英文→中文）正常工作。
"""

from __future__ import annotations

import json
import logging
import os

_log = logging.getLogger(__name__)


async def build_interface_translation_map(
    zh_summaries: list[str],
    output_language: str,
) -> dict[str, str]:
    """批量翻译接口名称，返回 {zh: en} 映射。

    英文模式：单次轻量 LLM 调用（<30 个短字符串，~1s）。
    中文模式或空列表：直接返回空 dict（零开销）。
    失败降级：返回空 dict，行为回退到中文（原行为不变）。
    """
    if output_language != "en" or not zh_summaries:
        return {}

    # 去重
    unique_summaries = list(dict.fromkeys(s.strip() for s in zh_summaries if s and s.strip()))
    if not unique_summaries:
        return {}

    try:
        return await _translate_via_llm(unique_summaries)
    except Exception as e:
        _log.warning("[interface_translator] LLM 翻译失败，回退空映射: %s", e)
        return {}


async def _translate_via_llm(summaries: list[str]) -> dict[str, str]:
    """通过 LLM 批量翻译接口名称。"""
    import httpx

    api_key = os.getenv("LLM_BINDING_API_KEY")
    base_url = os.getenv("LLM_BINDING_HOST", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    if not api_key:
        _log.warning("[interface_translator] LLM API key 未配置，跳过翻译")
        return {}

    name_list = "\n".join(f"- {s}" for s in summaries)
    prompt = (
        "You are an API interface name translator. "
        "Translate the following Chinese API interface names to concise English. "
        "Keep translations short (2-5 words), technical, and consistent. "
        "Output ONLY a JSON object mapping each Chinese name to its English translation. "
        "Do not add explanations or markdown.\n\n"
        f"Names to translate:\n{name_list}"
    )

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"].strip()

    # 解析 JSON，处理可能的 markdown 包裹
    if content.startswith("```"):
        # 去除 ```json ... ``` 包裹
        lines = content.split("\n")
        json_lines = [
            line for line in lines
            if not line.strip().startswith("```")
        ]
        content = "\n".join(json_lines)

    translation_map = json.loads(content)

    if not isinstance(translation_map, dict):
        _log.warning("[interface_translator] LLM 返回非 dict 类型: %s", type(translation_map))
        return {}

    # 验证：只保留原始列表中存在的 key
    validated = {}
    for zh, en in translation_map.items():
        if zh in summaries and isinstance(en, str) and en.strip():
            validated[zh] = en.strip()

    _log.info(
        "[interface_translator] 翻译完成: %d/%d 个接口名称",
        len(validated), len(summaries),
    )
    return validated


def reverse_translation_map(zh_to_en: dict[str, str]) -> dict[str, str]:
    """构建反向映射 {en: zh}。"""
    return {en: zh for zh, en in zh_to_en.items()}


def build_bilingual_table(zh_to_en: dict[str, str]) -> str:
    """构建双语对照表文本，注入到 LLM prompt 中。

    中文模式返回空串（不注入）。
    """
    if not zh_to_en:
        return ""

    lines = [
        "## Bilingual Interface Name Table (use English Name for dependencies):",
        "| Chinese Name | English Name |",
        "|---|---|",
    ]
    for zh, en in zh_to_en.items():
        lines.append(f"| {zh} | {en} |")
    return "\n".join(lines)


def postprocess_dependencies(cases: list[dict], zh_to_en: dict[str, str]) -> list[dict]:
    """后处理基础用例的 dependencies 字段，将中文名替换为英文名。

    仅处理英文模式（zh_to_en 非空时）。中文模式无操作。
    """
    if not zh_to_en or not cases:
        return cases

    for case in cases:
        deps = case.get("dependencies")
        if not deps or not isinstance(deps, list):
            continue
        new_deps = []
        for dep in deps:
            if isinstance(dep, str):
                dep_stripped = dep.strip()
                en = zh_to_en.get(dep_stripped)
                if en:
                    new_deps.append(en)
                else:
                    # 尝试子串匹配（LLM 可能加了前缀/后缀）
                    matched = False
                    for zh, en_candidate in zh_to_en.items():
                        if zh in dep_stripped or dep_stripped in zh:
                            new_deps.append(en_candidate)
                            matched = True
                            break
                    if not matched:
                        new_deps.append(dep)  # 保持原名
            else:
                new_deps.append(dep)
        case["dependencies"] = new_deps

    return cases
