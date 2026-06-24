import copy
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunVarContext:
    """Run-level temporary variables (serial suite/task sharing)."""

    temp_vars: dict[str, str] = field(default_factory=dict)


def prepare_runner_env(
    base_env_data: dict[str, Any],
    temp_vars: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Overlay temp vars onto envs; inject engine writeback buckets."""
    env_copy = copy.deepcopy(base_env_data)
    envs = dict(env_copy.get("envs") or {})
    if temp_vars:
        for key, value in temp_vars.items():
            envs[key] = value
    env_copy["envs"] = envs
    env_copy["debug_updates"] = {}
    return env_copy


def sync_temp_vars_from_engine(
    temp_vars: dict[str, str],
    base_envs: dict[str, str],
    engine_env: dict[str, Any],
) -> None:
    """Persist temp keys produced by save_env_variable (not global writeback)."""
    merged = dict(engine_env.get("envs") or {})
    debug_updates = engine_env.get("debug_updates") or {}
    if not isinstance(debug_updates, dict):
        debug_updates = {}
    for key, value in merged.items():
        if key in debug_updates:
            continue
        if key not in base_envs or merged[key] != base_envs.get(key):
            temp_vars[key] = str(value) if value is not None else ""


