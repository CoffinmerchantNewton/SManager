from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import Mapping, Sequence

from ...core.config import settings


@dataclass
class SSHResult:
    command: list[str]
    stdout: str
    stderr: str
    returncode: int


class SSHCommandError(RuntimeError):
    def __init__(self, result: SSHResult):
        super().__init__(result.stdout or result.stderr or f"command failed: {result.returncode}")
        self.result = result


class SSHClient:
    def __init__(self):
        self.host = settings.SERVER_SSH_HOST
        self.user = settings.SERVER_SSH_USER
        self.port = settings.SERVER_SSH_PORT
        self.timeout = settings.SERVER_SSH_TIMEOUT

    @property
    def is_local(self) -> bool:
        return not self.host or self.host in {"local", "localhost", "127.0.0.1"}

    def run(
        self,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = True,
    ) -> SSHResult:
        if self.is_local:
            full_command = self._local_command(command, cwd=cwd, env=env)
        else:
            full_command = self._ssh_command(command, cwd=cwd, env=env)
        completed = subprocess.run(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=self.timeout,
        )
        result = SSHResult(
            command=full_command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )
        if check and result.returncode != 0:
            raise SSHCommandError(result)
        return result

    def _local_command(
        self,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> list[str]:
        parts: list[str] = []
        if cwd:
            parts.extend(["cd", shell_token(cwd), "&&"])
        if env:
            parts.extend(f"{key}={shlex.quote(str(value))}" for key, value in env.items())
        parts.extend(shell_token(str(part)) for part in command)
        return ["bash", "-lc", " ".join(parts)]

    def _ssh_command(
        self,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> list[str]:
        target = f"{self.user}@{self.host}" if self.user else str(self.host)
        remote_parts: list[str] = []
        if cwd:
            remote_parts.extend(["cd", shell_token(cwd), "&&"])
        if env:
            remote_parts.extend(f"{key}={shlex.quote(str(value))}" for key, value in env.items())
        remote_parts.extend(shell_token(str(part)) for part in command)
        return [
            "ssh",
            "-p",
            str(self.port),
            "-o",
            f"ConnectTimeout={self.timeout}",
            target,
            " ".join(remote_parts),
        ]


def shell_token(value: str) -> str:
    if value.startswith("~/"):
        return "~/" + shlex.quote(value[2:])
    return shlex.quote(value)
