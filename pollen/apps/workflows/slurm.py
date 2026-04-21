import json
import subprocess
import uuid
from pathlib import Path

from django.conf import settings


class SlurmClient:
    def __init__(self, simulate=None):
        self.simulate = settings.SIMULATE_SLURM if simulate is None else simulate

    def render_batch_script(self, step_name, command_text, log_path, submit_arguments):
        lines = ["#!/bin/bash", "set -euo pipefail"]
        for key, value in submit_arguments.items():
            lines.append(f"#SBATCH --{key}={value}")
        lines.extend(
            [
                "",
                "echo \"[$(date '+%F %T')] start step\"",
                command_text,
                f"echo \"[$(date '+%F %T')] success\" >> \"{log_path}\"",
            ]
        )
        return "\n".join(lines) + "\n"

    def submit(self, script_path):
        if self.simulate:
            return f"SIM-{uuid.uuid4().hex[:8]}"
        result = subprocess.run(
            ["sbatch", str(script_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout.strip()
        return output.split()[-1]

    def query_state(self, job_id):
        if self.simulate:
            return {"state": "COMPLETED", "raw": "SIMULATED"}
        result = subprocess.run(
            ["squeue", "-h", "-j", str(job_id), "-o", "%T"],
            capture_output=True,
            text=True,
            check=False,
        )
        state = result.stdout.strip() or "UNKNOWN"
        return {"state": state, "raw": result.stdout.strip()}

    def accounting(self, job_id):
        if self.simulate:
            return {"state": "COMPLETED", "elapsed": "00:00:10", "exit_code": "0:0"}
        result = subprocess.run(
            ["sacct", "-j", str(job_id), "--parsable2", "--format=State,Elapsed,ExitCode"],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = [line for line in result.stdout.strip().splitlines() if line]
        if len(lines) >= 2:
            state, elapsed, exit_code = lines[1].split("|")[:3]
            return {"state": state, "elapsed": elapsed, "exit_code": exit_code}
        return {"state": "UNKNOWN", "elapsed": "", "exit_code": ""}

    def write_metadata(self, path, payload):
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
