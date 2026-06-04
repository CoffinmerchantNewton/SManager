from __future__ import annotations

import json
from typing import Any

from ...core.config import settings
from ..ssh import SSHClient


class ServerFlowService:
    def __init__(self, ssh: SSHClient | None = None):
        self.ssh = ssh or SSHClient()

    def plan(
        self,
        start: str,
        end: str,
        period: str,
        run_id: str | None = None,
        domain: str = "neimeng",
        variant: str = "official",
        met_provider: str = "FNL",
        commands_file: str | None = None,
    ) -> dict[str, Any]:
        args = [
            "plan",
            "--start",
            start,
            "--end",
            end,
            "--period",
            period,
            "--domain",
            domain,
            "--variant",
            variant,
            "--met-provider",
            met_provider,
        ]
        if run_id:
            args.extend(["--run-id", run_id])
        if commands_file:
            args.extend(["--commands-file", commands_file])
        return self._flow_json(args)

    def list_runs(self) -> dict[str, Any]:
        return self._flow_json(["list"])

    def status(self, run_id: str) -> dict[str, Any]:
        return self._flow_json(["status", "--run-id", run_id, "--json"])

    def fnl_verify(self, run_id: str | None = None, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        args = ["fnl-verify"]
        if run_id:
            args.extend(["--run-id", run_id])
        else:
            if not start or not end:
                raise ValueError("fnl_verify requires run_id or start/end")
            args.extend(["--start", start, "--end", end])
        return self._flow_json(args, check=False)

    def submit(self, run_id: str, dry_run: bool = False, allow_noop: bool = False) -> dict[str, Any]:
        args = ["submit", "--run-id", run_id]
        if dry_run:
            args.append("--dry-run")
        if allow_noop:
            args.append("--allow-noop")
        return self._flow_json(args, check=False)

    def logs(self, run_id: str, node: str | None = None, tail: int = 200) -> str:
        args = ["logs", "--run-id", run_id, "--tail", str(tail)]
        if node:
            args.extend(["--node", node])
        result = self._run_flow(args, check=False)
        return result.stdout

    def events(
        self,
        run_id: str,
        tail: int = 200,
        node: str | None = None,
        level: str | None = None,
        event_type: str | None = None,
    ) -> dict[str, Any]:
        args = ["events", "--run-id", run_id, "--tail", str(tail)]
        if node:
            args.extend(["--node", node])
        if level:
            args.extend(["--level", level])
        if event_type:
            args.extend(["--event-type", event_type])
        return self._flow_json(args, check=False)

    def diagnose(self, run_id: str) -> dict[str, Any]:
        return self._flow_json(["diagnose", "--run-id", run_id], check=False)

    def retry(self, run_id: str, node: str, dry_run: bool = False) -> dict[str, Any]:
        args = ["retry", "--run-id", run_id, "--node", node]
        if dry_run:
            args.append("--dry-run")
        return self._flow_json(args, check=False)

    def cancel(self, run_id: str, dry_run: bool = True) -> dict[str, Any]:
        args = ["cancel", "--run-id", run_id]
        if dry_run:
            args.append("--dry-run")
        return self._flow_json(args, check=False)

    def products(self, run_id: str) -> dict[str, Any]:
        return self._flow_json(["products", "--run-id", run_id], check=False)

    def collect_context(
        self,
        run_id: str,
        tail: int = 120,
        event_limit: int = 100,
        max_logs: int = 12,
    ) -> dict[str, Any]:
        return self._flow_json(
            [
                "collect-context",
                "--run-id",
                run_id,
                "--tail",
                str(tail),
                "--event-limit",
                str(event_limit),
                "--max-logs",
                str(max_logs),
            ],
            check=False,
        )

    def _flow_json(self, args: list[str], check: bool = True) -> dict[str, Any]:
        result = self._run_flow(args, check=check)
        payload = self._parse_json(result.stdout)
        payload.setdefault("_exit_code", result.returncode)
        if result.stderr:
            payload.setdefault("_stderr", result.stderr)
        return payload

    def _run_flow(self, args: list[str], check: bool = True):
        env = {}
        if settings.SERVER_FLOW_ROOT:
            env["AUTO_POLLEN_FLOW_ROOT"] = settings.SERVER_FLOW_ROOT
        if settings.SERVER_FNL_ROOTS:
            env["FNL_ROOTS"] = settings.SERVER_FNL_ROOTS
        elif settings.SERVER_FNL_UPLOAD_DIR:
            env["FNL_ROOTS"] = settings.SERVER_FNL_UPLOAD_DIR
        if settings.FNL_MIN_MB:
            env["FNL_MIN_MB"] = str(settings.FNL_MIN_MB)
        command = ["python3", settings.SERVER_FLOWCTL_PATH, *args]
        return self.ssh.run(command, cwd=settings.SERVER_FLOW_WORKDIR, env=env, check=check)

    @staticmethod
    def _parse_json(stdout: str) -> dict[str, Any]:
        text = stdout.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
            raise
