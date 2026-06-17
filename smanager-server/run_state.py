"""解析 run state.json（v1 细粒度 steps + 旧版 wps/real/wrf 字段）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

PIPELINE_STAGES = (
    "geogrid",
    "linkgrib",
    "ungrib",
    "metgrid",
    "real",
    "wrfchemi",
    "wrf",
    "postprocess",
)

WPS_SUBSTAGES = ("geogrid", "linkgrib", "ungrib", "metgrid")

DONE_STATE_VALUES = frozenset({"done", "success", "completed", "skipped"})
RUNNING_STATE_VALUES = frozenset({"running", "active"})
FAILED_STATE_VALUES = frozenset({"error", "failed", "fail", "failure"})


def _normalize_status(raw: Any) -> str:
    if raw is None:
        return "pending"
    text = str(raw).strip().lower()
    return text if text else "pending"


def _failure_stage(state: Dict[str, Any]) -> Optional[str]:
    failure = state.get("failure")
    if failure is None:
        return None
    if isinstance(failure, dict):
        raw = failure.get("step") or failure.get("stage")
        return str(raw).lower() if raw else None
    if isinstance(failure, str):
        return failure.lower()
    return None


def stage_status(state: Optional[Dict[str, Any]], stage: str) -> str:
    if not state:
        return "pending"

    steps = state.get("steps")
    if isinstance(steps, dict) and stage in steps:
        entry = steps[stage]
        if isinstance(entry, dict):
            return _normalize_status(entry.get("status"))
        return _normalize_status(entry)

    flat = state.get(stage)
    if isinstance(flat, str):
        return _normalize_status(flat)

    if stage in WPS_SUBSTAGES and "wps" in state:
        return _normalize_status(state["wps"])

    if flat is None:
        failed_stage = _failure_stage(state)
        if failed_stage == stage:
            return "failed"
        if failed_stage == "wps" and stage in WPS_SUBSTAGES:
            return "failed"
        return "pending"

    return _normalize_status(flat)


def step_detail(state: Optional[Dict[str, Any]], stage: str) -> Dict[str, Any]:
    if not state:
        return {}
    steps = state.get("steps")
    if isinstance(steps, dict) and stage in steps:
        entry = steps[stage]
        if isinstance(entry, dict):
            return dict(entry)
    return {}


def flatten_effective_state(state: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not state:
        return {}

    result = {stage: stage_status(state, stage) for stage in PIPELINE_STAGES}

    failed_stage = _failure_stage(state)
    if failed_stage == "wps":
        for sub in WPS_SUBSTAGES:
            if result[sub] in RUNNING_STATE_VALUES or result[sub] == "pending":
                result[sub] = "failed"
                break
    elif failed_stage and failed_stage in result:
        result[failed_stage] = "failed"

    return result


def has_granular_state(state: Optional[Dict[str, Any]]) -> bool:
    if not state:
        return False
    if isinstance(state.get("steps"), dict):
        return True
    return any(stage in state for stage in PIPELINE_STAGES)
