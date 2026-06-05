from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import FlowPaths
from .state import load_workflow


PATTERNS = [
    ("fnl_missing", ("MISSING", "missing fnl", "未找到合格 FNL")),
    ("fnl_bad_magic", ("bad_magic", "edition_num", "magic")),
    ("disk_full", ("No space left", "Disk quota exceeded")),
    ("slurm_submit_failed", ("sbatch", "Batch job submission failed")),
    ("wrf_cfl", ("cfl", "CFL", "exceeded cfl")),
    ("segfault", ("Segmentation fault", "SIGSEGV")),
]


def diagnose(paths: FlowPaths, run_id: str, tail_bytes: int = 200_000) -> dict[str, Any]:
    workflow = load_workflow(paths, run_id)
    nodes = workflow.get("nodes", [])
    node_status = {node.get("node"): node.get("status") for node in nodes}
    node_names = [name for name in node_status if name]
    findings = []
    for node in nodes:
        if node.get("status") == "error":
            findings.append(
                {
                    "node": node["node"],
                    "code": node.get("error_code") or "node_error",
                    "message": node.get("message"),
                    "suggested_action": suggested_action(node.get("error_code")),
                }
            )
    for log_path in paths.logs_dir(run_id).glob("*"):
        if not log_path.is_file():
            continue
        text = read_tail(log_path, tail_bytes)
        for code, needles in PATTERNS:
            if any(needle in text for needle in needles):
                node = infer_node(log_path, node_names)
                if node and node_status.get(node) == "success":
                    continue
                findings.append(
                    {
                        "node": node,
                        "code": code,
                        "message": f"matched {code} in {log_path.name}",
                        "suggested_action": suggested_action(code),
                    }
                )
    return {"run_id": run_id, "status": workflow.get("status"), "findings": findings}


def read_tail(path: Path, tail_bytes: int) -> str:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > tail_bytes:
            handle.seek(size - tail_bytes)
        return handle.read().decode("utf-8", errors="ignore")


def infer_node(path: Path, node_names: list[str] | None = None) -> str | None:
    name = path.name
    if node_names:
        for node in sorted(node_names, key=len, reverse=True):
            if name == node or name.startswith(f"{node}.") or name.startswith(f"{node}_"):
                return node
    return name.split("_", 1)[0] if "_" in name else None


def suggested_action(code: str | None) -> str:
    mapping = {
        "fnl_missing": "download_and_upload_missing_fnl",
        "fnl_bad_magic": "replace_bad_fnl_and_retry_ungrib",
        "disk_full": "notify_operator",
        "slurm_submit_failed": "retry_submit_later",
        "wrf_cfl": "restart_from_latest_restart_or_reduce_timestep",
        "segfault": "inspect_rsl_logs_before_retry",
        "node_command_missing": "configure_node_command",
    }
    return mapping.get(code or "", "inspect_logs")
