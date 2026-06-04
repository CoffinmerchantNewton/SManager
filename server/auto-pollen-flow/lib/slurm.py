from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any


def sbatch_available() -> bool:
    return shutil.which("sbatch") is not None


def submit_sbatch(script_path: Path, dependency: str | None = None) -> str:
    cmd = ["sbatch", "--parsable"]
    if dependency:
        cmd.append(f"--dependency=afterok:{dependency}")
    cmd.append(str(script_path))
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    output = result.stdout.strip()
    if result.returncode != 0:
        raise RuntimeError(output or f"sbatch failed with code {result.returncode}")
    job_id = output.split(";", 1)[0].strip()
    if not job_id:
        raise RuntimeError(f"sbatch returned empty job id: {output}")
    return job_id


def node_script(
    script_path: Path,
    flowctl: Path,
    run_id: str,
    node_name: str,
    node: dict[str, Any],
    log_dir: Path,
) -> None:
    slurm = node.get("slurm", {})
    partition = slurm.get("partition", os.environ.get("SLURM_PARTITION", "normal"))
    nodes = int(slurm.get("nodes", 1))
    ntasks = int(slurm.get("ntasks", 1))
    cpus = int(slurm.get("cpus_per_task", 1))
    walltime = slurm.get("walltime")
    lines = [
        "#!/bin/bash",
        f"#SBATCH -J pollen_{node_name}",
        f"#SBATCH -p {partition}",
        f"#SBATCH -N {nodes}",
        f"#SBATCH -n {ntasks}",
        f"#SBATCH --cpus-per-task={cpus}",
        f"#SBATCH -o {log_dir / (node_name + '_%j.out')}",
        f"#SBATCH -e {log_dir / (node_name + '_%j.err')}",
    ]
    if walltime:
        lines.append(f"#SBATCH -t {walltime}")
    command = " ".join(
        shlex.quote(part)
        for part in ["python3", str(flowctl), "run-node", "--run-id", run_id, "--node", node_name]
    )
    lines.extend(["", "set -eo pipefail", command, ""])
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("\n".join(lines), encoding="utf-8")
    script_path.chmod(0o755)
