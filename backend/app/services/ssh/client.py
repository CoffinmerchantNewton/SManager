from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
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
        self.password = settings.SERVER_SSH_PASSWORD

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
        elif self.password:
            return self._paramiko_run(command, cwd=cwd, env=env, check=check)
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

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        if self.is_local:
            raise RuntimeError("upload_file is only for remote SSH targets")
        if not self.password:
            raise RuntimeError("SERVER_SSH_PASSWORD is not configured")
        client = self._paramiko_client()
        try:
            sftp = client.open_sftp()
            try:
                self._sftp_mkdirs(sftp, str(Path(remote_path).parent).replace("\\", "/"))
                sftp.put(str(local_path), remote_path)
            finally:
                sftp.close()
        finally:
            client.close()

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
            "-o",
            "BatchMode=yes",
            "-o",
            "NumberOfPasswordPrompts=0",
            target,
            " ".join(remote_parts),
        ]

    def _paramiko_run(
        self,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = True,
    ) -> SSHResult:
        remote_parts: list[str] = []
        if cwd:
            remote_parts.extend(["cd", shell_token(cwd), "&&"])
        if env:
            remote_parts.extend(f"{key}={shlex.quote(str(value))}" for key, value in env.items())
        remote_parts.extend(shell_token(str(part)) for part in command)
        remote_command = " ".join(remote_parts)
        client = self._paramiko_client()
        try:
            _stdin, stdout, stderr = client.exec_command(remote_command, timeout=self.timeout)
            exit_status = stdout.channel.recv_exit_status()
            result = SSHResult(
                command=[*command],
                stdout=stdout.read().decode("utf-8", errors="replace"),
                stderr=stderr.read().decode("utf-8", errors="replace"),
                returncode=exit_status,
            )
        finally:
            client.close()
        if check and result.returncode != 0:
            raise SSHCommandError(result)
        return result

    def _paramiko_client(self):
        try:
            import paramiko
        except ImportError as exc:
            raise RuntimeError("paramiko is required when SERVER_SSH_PASSWORD is configured") from exc
        if not self.host:
            raise RuntimeError("SERVER_SSH_HOST is not configured")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=str(self.host),
            port=int(self.port),
            username=self.user,
            password=self.password,
            timeout=self.timeout,
            banner_timeout=self.timeout,
            auth_timeout=self.timeout,
        )
        return client

    @staticmethod
    def _sftp_mkdirs(sftp, remote_dir: str) -> None:
        parts = [part for part in remote_dir.split("/") if part]
        current = ""
        for part in parts:
            current += f"/{part}"
            try:
                sftp.stat(current)
            except OSError:
                sftp.mkdir(current)


def shell_token(value: str) -> str:
    if value.startswith("~/"):
        return "~/" + shlex.quote(value[2:])
    return shlex.quote(value)
