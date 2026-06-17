from __future__ import annotations

from typing import Any

from app.services.run_state import (
    DONE_STATE_VALUES,
    FAILED_STATE_VALUES,
    PIPELINE_STAGES,
    RUNNING_STATE_VALUES,
    flatten_effective_state,
    has_granular_state,
    step_detail,
)

RUN_KEY_SEP = "/"

STAGE_NODES = [(stage, stage) for stage in PIPELINE_STAGES]
STAGE_KEYS = list(PIPELINE_STAGES)

SLURM_ACTIVE_STATES = {"RUNNING", "PENDING", "CONFIGURING", "COMPLETING", "SUSPENDED"}
SLURM_FAILED_STATES = {"FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL", "PREEMPTED", "DEADLINE"}

STAGE_JOB_PREFIXES: dict[str, tuple[str, ...]] = {
    "geogrid": ("geogrid_", "prep_"),
    "linkgrib": ("prep_", "linkgrib_"),
    "ungrib": ("prep_", "ungrib_"),
    "metgrid": ("prep_", "metgrid_"),
    "real": ("real_", "prep_"),
    "wrfchemi": ("wrfchemi_", "chemi_", "prep_"),
    "wrf": ("wrf_",),
    "postprocess": ("post_", "postprocess_"),
    # 旧版 state 兼容
    "wps": ("wps_", "geogrid_", "prep_"),
}


def parse_run_key(run_key: str) -> tuple[str, str, str]:
    parts = [part for part in run_key.split(RUN_KEY_SEP) if part]
    if len(parts) != 3:
        raise ValueError("run_key must be season/region/run_id")
    return parts[0], parts[1], parts[2]


def build_run_key(season: str, region: str, run_id: str) -> str:
    return RUN_KEY_SEP.join([season.lower(), region.lower(), run_id])


def run_sort_key(run: dict[str, Any]) -> tuple[str, str]:
    return str(run.get("start_date") or run.get("start_time") or ""), str(run.get("run_id") or "")


def sort_runs_newest_first(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(runs, key=run_sort_key, reverse=True)


def _job_name_matches_run(job_name: str, region: str, season: str, run_id: str) -> bool:
    name = (job_name or "").lower()
    tag = f"{region.lower()}_{season.lower()}_{run_id.lower()}"
    if tag in name:
        return True
    return region.lower() in name and season.lower() in name and run_id.lower() in name


def _job_matches_stage(job_name: str, stage: str) -> bool:
    name = (job_name or "").lower()
    for prefix in STAGE_JOB_PREFIXES.get(stage, ()):
        if name.startswith(prefix) or f"_{prefix}" in name:
            return True
    return False


def _pick_stage_job(slurm_jobs: list[dict[str, Any]], stage: str) -> dict[str, Any] | None:
    matched = [job for job in slurm_jobs if _job_matches_stage(job.get("name", ""), stage)]
    if not matched:
        return None
    for job in matched:
        if (job.get("state") or "").upper() in SLURM_ACTIVE_STATES:
            return job
    return matched[0]


def _resolve_effective_state(run: dict[str, Any]) -> dict[str, str]:
    raw_state = run.get("state") or {}
    server_effective = run.get("effective_state") or {}

    if has_granular_state(raw_state):
        base = flatten_effective_state(raw_state)
    elif has_granular_state(server_effective):
        base = {stage: str(server_effective.get(stage, "pending")).lower() for stage in PIPELINE_STAGES}
    elif server_effective and any(k in server_effective for k in ("wps", "real", "wrfchemi", "wrf", "postprocess")):
        base = flatten_effective_state(raw_state if raw_state else server_effective)
    else:
        base = flatten_effective_state(raw_state if raw_state else server_effective)

    for stage in PIPELINE_STAGES:
        override = server_effective.get(stage)
        if override is None:
            continue
        normalized = str(override).lower()
        if normalized in FAILED_STATE_VALUES:
            base[stage] = normalized
        elif normalized in RUNNING_STATE_VALUES and base.get(stage) == "pending":
            base[stage] = normalized

    return base


def derive_run_status(run: dict[str, Any]) -> str:
    slurm_jobs = run.get("slurm_jobs") or []
    if any((job.get("state") or "").upper() in SLURM_ACTIVE_STATES for job in slurm_jobs):
        return "running"
    if any((job.get("state") or "").upper() in SLURM_FAILED_STATES for job in slurm_jobs):
        return "error"

    state = _resolve_effective_state(run)
    anomalies = run.get("anomalies") or []
    stage_values = {key: state.get(key, "pending") for key in STAGE_KEYS}

    if any(value in FAILED_STATE_VALUES for value in stage_values.values()):
        return "error"
    if anomalies and any(value in RUNNING_STATE_VALUES for value in stage_values.values()):
        return "error"

    if any(value in RUNNING_STATE_VALUES for value in stage_values.values()):
        return "running"

    done_count = sum(1 for key in STAGE_KEYS if stage_values[key] in DONE_STATE_VALUES)
    if done_count == len(STAGE_KEYS):
        return "success"
    if done_count > 0:
        return "running"

    raw_state = run.get("state") or {}
    if not raw_state and not run.get("effective_state"):
        return "pending"
    return "ready"


def compute_run_progress(run: dict[str, Any], status: str) -> float:
    state = _resolve_effective_state(run)
    done_count = sum(1 for key in STAGE_KEYS if state.get(key, "pending") in DONE_STATE_VALUES)
    progress = (done_count / len(STAGE_KEYS)) * 100.0

    wrf_frac = run.get("progress")
    if wrf_frac is not None and isinstance(wrf_frac, (int, float)):
        wrf_pct = float(wrf_frac) * 100.0 if float(wrf_frac) <= 1.0 else float(wrf_frac)
        wrf_idx = STAGE_KEYS.index("wrf")
        base = (wrf_idx / len(STAGE_KEYS)) * 100.0
        progress = base + (wrf_pct / len(STAGE_KEYS))

    if status == "success":
        return 100.0
    if status == "pending":
        return 0.0
    return round(min(100.0, max(0.0, progress)), 1)


def state_to_nodes(run: dict[str, Any]) -> list[dict[str, Any]]:
    state = _resolve_effective_state(run)
    raw_state = run.get("state") or {}
    slurm_jobs = run.get("slurm_jobs") or []
    nodes: list[dict[str, Any]] = []

    for stage_key, node_name in STAGE_NODES:
        raw = state.get(stage_key, "pending")
        detail = step_detail(raw_state, stage_key)
        stage_job = _pick_stage_job(slurm_jobs, stage_key)
        job_state = (stage_job.get("state") or "").upper() if stage_job else ""

        if raw in DONE_STATE_VALUES:
            node_status = "success"
            progress = 100
        elif raw in FAILED_STATE_VALUES or job_state in SLURM_FAILED_STATES:
            node_status = "error"
            progress = 0
            raw = raw if raw in FAILED_STATE_VALUES else "failed"
        elif raw in RUNNING_STATE_VALUES or job_state in SLURM_ACTIVE_STATES:
            node_status = "running"
            progress = 50
        else:
            node_status = "pending"
            progress = 0

        message_parts = [raw]
        if detail.get("started_at"):
            message_parts.append(f"start={detail['started_at']}")
        if detail.get("finished_at"):
            message_parts.append(f"end={detail['finished_at']}")
        if stage_job:
            message_parts.append(f"slurm {stage_job.get('job_id')} {stage_job.get('state')}")

        nodes.append(
            {
                "node": node_name,
                "stage": stage_key,
                "status": node_status,
                "progress": progress,
                "attempt": 0,
                "started_at": detail.get("started_at"),
                "finished_at": detail.get("finished_at"),
                "slurm_job_id": stage_job.get("job_id") if stage_job else None,
                "slurm_state": stage_job.get("state") if stage_job else None,
                "slurm_job_name": stage_job.get("name") if stage_job else None,
                "message": " | ".join(message_parts),
            }
        )
    return nodes


def serialize_server_run(run: dict[str, Any]) -> dict[str, Any]:
    season = str(run.get("season") or "")
    region = str(run.get("region") or "")
    run_id = str(run.get("run_id") or "")
    effective_state = _resolve_effective_state(run)
    status = derive_run_status({**run, "effective_state": effective_state})
    progress = compute_run_progress({**run, "effective_state": effective_state}, status)
    slurm_jobs = run.get("slurm_jobs") or []
    active_jobs = [job for job in slurm_jobs if (job.get("state") or "").upper() in SLURM_ACTIVE_STATES]
    raw_state = run.get("state") or {}
    failure = raw_state.get("failure")

    return {
        "run_key": build_run_key(season, region, run_id),
        "run_id": run_id,
        "season": season,
        "region": region,
        "pre": run.get("pre"),
        "start_date": run.get("start_date"),
        "status": status,
        "progress": progress,
        "server_run_dir": run.get("run_root"),
        "state": raw_state,
        "effective_state": effective_state,
        "failure": failure,
        "anomalies": run.get("anomalies") or [],
        "slurm_jobs": slurm_jobs,
        "slurm_active_count": len(active_jobs),
        "slurm_job_ids": [job.get("job_id") for job in active_jobs if job.get("job_id")],
        "nodes": state_to_nodes({**run, "effective_state": effective_state}),
        "period": season,
        "domain": region,
        "start_time": run.get("start_date"),
        "end_time": None,
        "variant": run.get("pre"),
        "last_error": _last_error(run, failure),
    }


def _last_error(run: dict[str, Any], failure: Any) -> str | None:
    if isinstance(failure, dict):
        msg = failure.get("message") or failure.get("error")
        if msg:
            return str(msg)
        step = failure.get("step") or failure.get("stage")
        if step:
            return f"failure at {step}"
    if isinstance(failure, str) and failure.strip():
        return failure
    anomalies = run.get("anomalies") or []
    return str(anomalies[0]) if anomalies else None


def run_log_candidates(run: dict[str, Any]) -> list[tuple[str, str]]:
    season = str(run.get("season") or "").lower()
    region = str(run.get("region") or "").lower()
    run_id = str(run.get("run_id") or "")
    base = f"predict/{season}/{region}/{run_id}"
    state = _resolve_effective_state(run)

    candidates: list[tuple[str, str]] = [
        ("wps_log", f"{base}/wps/wps.log"),
        ("geogrid_log", f"{base}/wps/geogrid.log"),
        ("real_log", f"{base}/real/real.log"),
        ("prep_log", f"{base}/prep.log"),
        ("wrf_log", f"{base}/wrf/wrf.log"),
        ("wrf_rsl_out", f"{base}/wrf/rsl.out.0000"),
        ("wrf_rsl_error", f"{base}/wrf/rsl.error.0000"),
    ]

    stage_order = list(STAGE_KEYS)
    current_stage = None
    for stage in reversed(stage_order):
        raw = state.get(stage, "pending")
        if raw in RUNNING_STATE_VALUES or raw in DONE_STATE_VALUES:
            current_stage = stage
            break

    if current_stage:
        stage_first = [
            item
            for item in candidates
            if current_stage in item[0] or current_stage.split("_")[0] in item[0]
        ]
        rest = [item for item in candidates if item not in stage_first]
        candidates = stage_first + rest

    return candidates


def _is_missing_file_error(error: str | None) -> bool:
    if not error:
        return False
    lower = error.lower()
    return (
        "404" in lower
        or "不存在" in error
        or "not found" in lower
        or "file not found" in lower
    )


def collect_log_tails(run: dict[str, Any], *, lines: int, tail_file) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for name, path in run_log_candidates(run):
        result = tail_file("runs", path, lines=lines, live=True)
        payload = result.data or {}
        tail_lines = payload.get("lines") or []
        if tail_lines:
            entries.append({"name": name, "path": path, "size_bytes": 0, "tail": tail_lines})
            continue
        if result.error and not _is_missing_file_error(result.error):
            entries.append(
                {
                    "name": name,
                    "path": path,
                    "size_bytes": 0,
                    "tail": [f"[unavailable] {result.error}"],
                    "error": result.error,
                }
            )
    return entries
