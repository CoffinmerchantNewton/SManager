from __future__ import annotations

from pathlib import Path
from typing import Any

from .jsonio import append_jsonl, read_json, write_json_atomic
from .paths import FlowPaths
from .timeutils import now_iso
from .wrf_progress import enrich_wrf_run_node


TERMINAL_STATUSES = {"success", "error", "skipped", "cancelled"}


def load_spec(paths: FlowPaths, run_id: str) -> dict[str, Any]:
    spec = read_json(paths.run_spec(run_id))
    if not spec:
        raise FileNotFoundError(f"run spec not found: {paths.run_spec(run_id)}")
    return spec


def node_names(spec: dict[str, Any]) -> list[str]:
    return [node["name"] for node in spec.get("nodes", [])]


def write_event(
    paths: FlowPaths,
    run_id: str,
    event_type: str,
    message: str,
    node: str | None = None,
    level: str = "info",
    payload: dict[str, Any] | None = None,
) -> None:
    append_jsonl(
        paths.events(run_id),
        {
            "run_id": run_id,
            "node": node,
            "level": level,
            "event_type": event_type,
            "message": message,
            "payload": payload or {},
            "created_at": now_iso(),
        },
    )


def initial_node_status(run_id: str, node: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "node": node,
        "status": "pending",
        "progress": 0,
        "attempt": 0,
        "slurm_job_id": None,
        "started_at": None,
        "updated_at": now_iso(),
        "finished_at": None,
        "error_code": None,
        "message": "pending",
        "inputs": [],
        "outputs": [],
        "log_files": [],
    }


def initialize_run(paths: FlowPaths, spec: dict[str, Any]) -> None:
    run_id = spec["run_id"]
    paths.run_dir(run_id).mkdir(parents=True, exist_ok=True)
    paths.state_dir(run_id).mkdir(parents=True, exist_ok=True)
    paths.logs_dir(run_id).mkdir(parents=True, exist_ok=True)
    paths.slurm_dir(run_id).mkdir(parents=True, exist_ok=True)
    paths.products_dir(run_id).mkdir(parents=True, exist_ok=True)
    write_json_atomic(paths.run_spec(run_id), spec)
    for node in node_names(spec):
        status_path = paths.node_status(run_id, node)
        if not status_path.exists():
            write_json_atomic(status_path, initial_node_status(run_id, node))
    refresh_workflow(paths, run_id)
    write_event(paths, run_id, "planned", "run planned")


def load_node_status(paths: FlowPaths, run_id: str, node: str) -> dict[str, Any]:
    status = read_json(paths.node_status(run_id, node))
    return status or initial_node_status(run_id, node)


def update_node_status(
    paths: FlowPaths,
    run_id: str,
    node: str,
    status: str,
    message: str,
    progress: int | None = None,
    error_code: str | None = None,
    slurm_job_id: str | None = None,
    log_files: list[str] | None = None,
    outputs: list[str] | None = None,
) -> dict[str, Any]:
    data = load_node_status(paths, run_id, node)
    previous = data.get("status")
    if status == "running" and previous != "running":
        data["started_at"] = data.get("started_at") or now_iso()
        data["attempt"] = int(data.get("attempt") or 0) + 1
    if status in TERMINAL_STATUSES:
        data["finished_at"] = now_iso()
    data["status"] = status
    data["message"] = message
    data["updated_at"] = now_iso()
    if progress is not None:
        data["progress"] = progress
    if error_code is not None:
        data["error_code"] = error_code
    if slurm_job_id is not None:
        data["slurm_job_id"] = slurm_job_id
    if log_files is not None:
        data["log_files"] = log_files
    if outputs is not None:
        data["outputs"] = outputs
    write_json_atomic(paths.node_status(run_id, node), data)
    write_event(
        paths,
        run_id,
        "node_status",
        message,
        node=node,
        level="error" if status == "error" else "info",
        payload={"status": status, "error_code": data.get("error_code")},
    )
    refresh_workflow(paths, run_id)
    return data


def workflow_summary(paths: FlowPaths, run_id: str) -> dict[str, Any]:
    spec = load_spec(paths, run_id)
    nodes = [enrich_wrf_run_node(paths, spec, load_node_status(paths, run_id, node)) for node in node_names(spec)]
    total = len(nodes) or 1
    terminal = sum(1 for node in nodes if node["status"] in TERMINAL_STATUSES)
    errors = [node for node in nodes if node["status"] == "error"]
    running = [node for node in nodes if node["status"] == "running"]
    cancelled = [node for node in nodes if node["status"] == "cancelled"]
    if cancelled:
        status = "cancelled"
    elif errors:
        status = "error"
    elif running:
        status = "running"
    elif terminal == len(nodes):
        status = "success"
    elif any(node["status"] == "retrying" for node in nodes):
        status = "retrying"
    else:
        status = "pending"
    return {
        "run_id": run_id,
        "status": status,
        "progress": round(terminal * 100 / total, 2),
        "updated_at": now_iso(),
        "nodes": nodes,
        "run_spec_path": str(paths.run_spec(run_id)),
    }


def refresh_workflow(paths: FlowPaths, run_id: str) -> dict[str, Any]:
    summary = workflow_summary(paths, run_id)
    write_json_atomic(paths.workflow_status(run_id), summary)
    return summary


def load_workflow(paths: FlowPaths, run_id: str) -> dict[str, Any]:
    status = read_json(paths.workflow_status(run_id))
    return status or refresh_workflow(paths, run_id)


def list_runs(paths: FlowPaths) -> list[dict[str, Any]]:
    if not paths.runs_dir.exists():
        return []
    runs = []
    for item in sorted(paths.runs_dir.iterdir()):
        if not item.is_dir():
            continue
        try:
            runs.append(load_workflow(paths, item.name))
        except (FileNotFoundError, ValueError):
            continue
    return runs
