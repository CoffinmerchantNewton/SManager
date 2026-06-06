from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from lib.fnl import roots_from_env
from lib.slurm import sbatch_available, scancel_available


REQUIRED_NODE_ENV = {
    "wps_geogrid": "WPS_GEOGRID_COMMAND",
    "wps_ungrib": "WPS_UNGRIB_COMMAND",
    "wps_metgrid": "WPS_METGRID_COMMAND",
    "wrf_setup": "WRF_SETUP_COMMAND",
    "real": "REAL_COMMAND",
    "compute_gdd": "COMPUTE_GDD_COMMAND",
    "prep_pollen": "PREP_POLLEN_COMMAND",
    "wrf_run": "WRF_RUN_COMMAND",
    "postprocess_eval": "POSTPROCESS_EVAL_COMMAND",
}


def configured_node_order(config: dict[str, Any]) -> list[str]:
    raw_order = config.get("node_order")
    if raw_order is None:
        return list(REQUIRED_NODE_ENV)
    if not isinstance(raw_order, list) or not all(isinstance(name, str) and name for name in raw_order):
        return []
    return raw_order


def run_preflight(flow_root: Path, command_config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = command_config or {}
    env = _string_map(config.get("env", {}))
    node_configs = config.get("nodes", {}) if isinstance(config.get("nodes", {}), dict) else {}

    checks = [
        check_command("python", env.get("PYTHON_BIN") or sys.executable or "python3", required=True),
        check_command("bash", "bash", required=True),
        check_command("sbatch", "sbatch", required=False),
        check_command("scancel", "scancel", required=False),
        check_path("flow_root", flow_root, required=True, kind="dir", writable=True),
    ]

    for key in ["NODE_COMMAND_DIR", "AUTO_POLLEN_ROOT", "ENV_SCRIPT", "WPS_WORK_DIR", "WRF_RUN_DIR"]:
        value = env.get(key)
        if value:
            checks.append(check_path(key.lower(), Path(value), required=key in {"NODE_COMMAND_DIR", "AUTO_POLLEN_ROOT"}))

    checks.extend(check_fnl_roots(env))
    checks.extend(check_node_commands(env, node_configs, configured_node_order(config)))

    slurm_defaults = config.get("slurm_defaults", {})
    if isinstance(slurm_defaults, dict):
        checks.append(check_slurm_defaults(slurm_defaults))

    ok = all(item["ok"] or not item.get("required", True) for item in checks)
    return {
        "ok": ok,
        "host": platform.node(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "flow_root": str(flow_root),
        "sbatch_available": sbatch_available(),
        "scancel_available": scancel_available(),
        "checks": checks,
        "summary": summarize_checks(checks),
    }


def check_command(name: str, command: str, required: bool) -> dict[str, Any]:
    executable = command.split()[0]
    resolved = shutil.which(executable) if not Path(executable).is_absolute() else executable
    ok = bool(resolved and Path(resolved).exists()) if Path(str(resolved)).is_absolute() else bool(resolved)
    return {
        "name": f"command:{name}",
        "ok": ok,
        "required": required,
        "command": command,
        "resolved": str(resolved) if resolved else None,
        "message": "available" if ok else "not found on PATH",
    }


def check_path(name: str, path: Path, required: bool, kind: str | None = None, writable: bool = False) -> dict[str, Any]:
    exists = path.exists()
    expected_kind = kind or ("file" if path.suffix else "dir")
    kind_ok = exists and ((expected_kind == "file" and path.is_file()) or (expected_kind == "dir" and path.is_dir()))
    write_ok = True
    if writable and kind_ok:
        write_ok = can_write(path)
    ok = kind_ok and write_ok
    message = "ok" if ok else "missing"
    if exists and not kind_ok:
        message = f"expected {expected_kind}"
    if kind_ok and not write_ok:
        message = "not writable"
    return {
        "name": f"path:{name}",
        "ok": ok,
        "required": required,
        "path": str(path),
        "kind": expected_kind,
        "writable": writable,
        "message": message,
    }


def check_fnl_roots(config_env: dict[str, str] | None = None) -> list[dict[str, Any]]:
    roots = roots_from_config(config_env or {}) or roots_from_env()
    if not roots:
        return [
            {
                "name": "fnl_roots",
                "ok": False,
                "required": True,
                "roots": [],
                "message": "FNL_ROOTS or FNL_ROOT/FNL_FALLBACK_ROOT is not configured",
            }
        ]
    return [check_path(f"fnl_root:{index}", root, required=index == 0, kind="dir") for index, root in enumerate(roots)]


def roots_from_config(config_env: dict[str, str]) -> list[Path]:
    raw = config_env.get("FNL_ROOTS")
    if raw:
        return [Path(part) for part in raw.split(":") if part]
    return [Path(config_env[key]) for key in ("FNL_ROOT", "FNL_FALLBACK_ROOT") if config_env.get(key)]


def check_node_commands(global_env: dict[str, str], node_configs: dict[str, Any], node_order: list[str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not node_order:
        return [
            {
                "name": "node_order",
                "ok": False,
                "required": True,
                "message": "node_order must be a list of node names",
            }
        ]
    for node_name in node_order:
        required_env = REQUIRED_NODE_ENV.get(node_name)
        node = node_configs.get(node_name, {}) if isinstance(node_configs.get(node_name, {}), dict) else {}
        node_env = dict(global_env)
        node_env.update(_string_map(node.get("env", {})))
        command = node.get("command")
        command_env_value = node_env.get(required_env) if required_env else None
        ok = bool(command and (command_env_value or required_env is None))
        checks.append(
            {
                "name": f"node:{node_name}",
                "ok": ok,
                "required": True,
                "node": node_name,
                "command": command,
                "required_env": required_env,
                "configured_value": command_env_value,
                "message": "configured" if ok else f"missing {required_env or 'node command'}",
            }
        )
    return checks


def check_slurm_defaults(slurm_defaults: dict[str, Any]) -> dict[str, Any]:
    required = ["partition", "nodes", "ntasks", "cpus_per_task"]
    missing = [key for key in required if key not in slurm_defaults]
    return {
        "name": "slurm_defaults",
        "ok": not missing,
        "required": True,
        "missing": missing,
        "message": "configured" if not missing else f"missing {', '.join(missing)}",
    }


def can_write(path: Path) -> bool:
    target = path / ".preflight_write_check" if path.is_dir() else path
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ok\n", encoding="utf-8")
        if target.name == ".preflight_write_check":
            target.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, int]:
    failed_required = [item for item in checks if not item["ok"] and item.get("required", True)]
    failed_optional = [item for item in checks if not item["ok"] and not item.get("required", True)]
    return {
        "total": len(checks),
        "failed_required": len(failed_required),
        "failed_optional": len(failed_optional),
    }


def _string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def command_output(command: list[str]) -> str:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    return result.stdout.strip()
