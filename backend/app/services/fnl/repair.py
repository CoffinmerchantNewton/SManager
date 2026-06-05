from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ...core.config import settings
from ...models.models import FnlFileRecord
from ..audit import create_action, finish_action
from ..flow import ServerFlowService
from ..ssh import SSHClient


REPAIR_STATUSES = {"missing", "bad_magic", "too_small", "link_broken"}


class FnlRepairService:
    def __init__(
        self,
        db: Session,
        flow: ServerFlowService | None = None,
        ssh: SSHClient | None = None,
    ):
        self.db = db
        self.flow = flow or ServerFlowService()
        self.ssh = ssh or SSHClient()

    def verify_server(
        self,
        run_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        manifest = self.flow.fnl_verify(run_id=run_id, start=start, end=end)
        self.upsert_records(manifest)
        return manifest

    def repair(
        self,
        run_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        action = create_action(
            self.db,
            action_type="fnl_repair",
            status="running",
            run_id=run_id,
            reason="repair missing or invalid FNL files",
            input_data={"run_id": run_id, "start": start, "end": end},
        )
        initial = self.verify_server(run_id=run_id, start=start, end=end)
        targets = [item for item in initial.get("files", []) if item.get("needs_repair")]
        repairs = []
        if not targets:
            ok = bool(initial.get("ok"))
            output = {"ok": ok, "initial": initial, "repairs": repairs, "final": initial}
            finish_action(self.db, action, "success" if ok else "error", output)
            return output

        for item in targets:
            result = self.repair_one(item)
            repairs.append(result)

        final = self.verify_server(run_id=run_id, start=start, end=end)
        ok = bool(final.get("ok")) and all(item.get("ok") for item in repairs)
        output = {"ok": ok, "initial": initial, "repairs": repairs, "final": final}
        finish_action(self.db, action, "success" if ok else "error", output)
        return output

    def repair_one(self, item: dict[str, Any]) -> dict[str, Any]:
        valid_time = item["valid_time"]
        file_name = item["file_name"]
        record = self.get_or_create_record(valid_time, file_name)
        record.repair_attempt = int(record.repair_attempt or 0) + 1
        record.status = item.get("status")
        self.db.commit()

        try:
            local_path = self.ensure_downloaded(item)
            remote_path = self.upload(local_path, valid_time, file_name)
            record.local_path = str(local_path)
            record.server_path = remote_path
            record.uploaded = True
            record.error_message = None
            self.db.commit()
            return {
                "ok": True,
                "valid_time": valid_time,
                "file_name": file_name,
                "local_path": str(local_path),
                "server_path": remote_path,
            }
        except Exception as exc:
            record.error_message = str(exc)
            record.uploaded = False
            self.db.commit()
            return {
                "ok": False,
                "valid_time": valid_time,
                "file_name": file_name,
                "error": exc.__class__.__name__,
                "message": str(exc),
            }

    def ensure_downloaded(self, item: dict[str, Any]) -> Path:
        path = self.cache_path(item["valid_time"], item["file_name"])
        if self.local_fnl_valid(path):
            return path
        command = settings.FNL_DOWNLOAD_COMMAND
        if not command:
            raise RuntimeError("FNL_DOWNLOAD_COMMAND is not configured")
        path.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update(
            {
                "FNL_VALID_TIME": item["valid_time"],
                "FNL_FILE_NAME": item["file_name"],
                "FNL_OUTPUT_PATH": str(path),
            }
        )
        result = subprocess.run(
            command,
            shell=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FNL download command failed: {result.stdout.strip()}")
        if not self.local_fnl_valid(path):
            raise RuntimeError(f"Downloaded FNL failed validation: {path}")
        return path

    def upload(self, local_path: Path, valid_time: str, file_name: str) -> str:
        upload_root = settings.SERVER_FNL_UPLOAD_DIR
        if not upload_root:
            raise RuntimeError("SERVER_FNL_UPLOAD_DIR is not configured")
        day = valid_time[:8]
        year = valid_time[:4]
        remote_dir = f"{upload_root.rstrip('/')}/{year}/{day}"
        remote_path = f"{remote_dir}/{file_name}"
        if self.ssh.is_local:
            Path(remote_dir).mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, remote_path)
            return remote_path
        if settings.SERVER_SSH_PASSWORD:
            self.ssh.upload_file(local_path, remote_path)
            return remote_path

        self.ssh.run(["mkdir", "-p", remote_dir])
        method = settings.FNL_UPLOAD_METHOD.lower()
        if method == "rsync" and shutil.which("rsync"):
            self.run_rsync(local_path, remote_path)
        else:
            self.run_scp(local_path, remote_path)
        return remote_path

    def run_rsync(self, local_path: Path, remote_path: str) -> None:
        target = self.remote_target(remote_path)
        ssh_cmd = f"ssh -p {settings.SERVER_SSH_PORT}"
        result = subprocess.run(
            ["rsync", "-av", "--partial", "-e", ssh_cmd, str(local_path), target],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"rsync upload failed: {result.stdout.strip()}")

    def run_scp(self, local_path: Path, remote_path: str) -> None:
        target = self.remote_target(remote_path)
        result = subprocess.run(
            ["scp", "-P", str(settings.SERVER_SSH_PORT), str(local_path), target],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"scp upload failed: {result.stdout.strip()}")

    def remote_target(self, remote_path: str) -> str:
        host = settings.SERVER_SSH_HOST
        if not host:
            raise RuntimeError("SERVER_SSH_HOST is not configured for remote upload")
        user_host = f"{settings.SERVER_SSH_USER}@{host}" if settings.SERVER_SSH_USER else host
        return f"{user_host}:{remote_path}"

    def local_fnl_valid(self, path: Path) -> bool:
        if not path.is_file():
            return False
        if path.stat().st_size < int(settings.FNL_MIN_MB * 1024 * 1024):
            return False
        try:
            with path.open("rb") as handle:
                return handle.read(4) == b"GRIB"
        except OSError:
            return False

    def cache_path(self, valid_time: str, file_name: str) -> Path:
        day = valid_time[:8]
        year = valid_time[:4]
        return Path(settings.JUMPBOX_FNL_CACHE_DIR) / year / day / file_name

    def upsert_records(self, manifest: dict[str, Any]) -> None:
        for item in manifest.get("files", []):
            record = self.get_or_create_record(item.get("valid_time"), item.get("file_name"))
            record.status = item.get("status")
            record.source = item.get("source")
            record.server_path = item.get("server_path")
            record.size_bytes = item.get("size_bytes")
            record.valid_grib = bool(item.get("valid_grib"))
            record.checked_at = item.get("checked_at")
        self.db.commit()

    def get_or_create_record(self, valid_time: str, file_name: str) -> FnlFileRecord:
        record = (
            self.db.query(FnlFileRecord)
            .filter(FnlFileRecord.valid_time == valid_time, FnlFileRecord.file_name == file_name)
            .first()
        )
        if not record:
            record = FnlFileRecord(valid_time=valid_time, file_name=file_name)
            self.db.add(record)
            self.db.flush()
        return record
