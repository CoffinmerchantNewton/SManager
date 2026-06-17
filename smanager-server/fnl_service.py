"""FNL 上传、校验与归档。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile

from file_tree import ensure_staging_dir
from models import AppConfig, FnlCompleteResult, FnlUploadResult, FnlVerifyResult

FNL_NAME_RE = re.compile(r"^fnl_(\d{8})_(\d{2})_00\.grib2$")


def validate_filename(filename: str) -> tuple[str, str, str]:
    match = FNL_NAME_RE.match(filename)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="文件名须为 fnl_YYYYMMDD_HH_00.grib2",
        )
    date_str, hour = match.group(1), match.group(2)
    if hour not in {"00", "06", "12", "18"}:
        raise HTTPException(status_code=400, detail="FNL 时次仅支持 00/06/12/18")
    return filename, date_str, hour


def _is_grib_header(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"GRIB"
    except OSError:
        return False


def _wgrib2_inventory(path: Path, wgrib2_bin: str) -> tuple[bool, str]:
    if not Path(wgrib2_bin).is_file():
        return False, "wgrib2 不可用"
    try:
        proc = subprocess.run(
            [wgrib2_bin, str(path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout or "wgrib2 失败").strip()[:500]
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        return len(lines) > 0, f"inventory_lines={len(lines)}"
    except subprocess.TimeoutExpired:
        return False, "wgrib2 超时"
    except OSError as exc:
        return False, str(exc)


def verify_staging_file(config: AppConfig, filename: str) -> FnlVerifyResult:
    validate_filename(filename)
    staging = ensure_staging_dir(config)
    path = staging / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="staging 中无此文件")

    min_bytes = int(config.paths.fnl_min_mb * 1024 * 1024)
    size = path.stat().st_size
    checks: dict = {
        "exists": True,
        "size_ok": size >= min_bytes,
        "size_bytes": size,
        "grib_header": _is_grib_header(path),
    }
    inv_ok, inv_msg = _wgrib2_inventory(path, config.paths.wgrib2)
    checks["wgrib2"] = inv_ok
    checks["wgrib2_detail"] = inv_msg

    valid = all([checks["size_ok"], checks["grib_header"], checks["wgrib2"]])
    return FnlVerifyResult(
        filename=filename,
        valid=valid,
        size_bytes=size,
        checks=checks,
        message="校验通过" if valid else "校验未通过",
    )


async def save_upload(config: AppConfig, upload: UploadFile) -> FnlUploadResult:
    if not upload.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    filename, _, _ = validate_filename(upload.filename)
    staging = ensure_staging_dir(config)
    dest = staging / filename
    part = staging / f"{filename}.uploading"

    size = 0
    try:
        with part.open("wb") as handle:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                size += len(chunk)
        os.replace(part, dest)
    except OSError as exc:
        part.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"写入失败: {exc}") from exc
    finally:
        await upload.close()

    return FnlUploadResult(
        filename=filename,
        staging_path=str(dest),
        size_bytes=size,
        message="已上传到 staging，请调用 verify/complete",
    )


def complete_upload(config: AppConfig, filename: str, force: bool = False) -> FnlCompleteResult:
    result = verify_staging_file(config, filename)
    if not result.valid and not force:
        raise HTTPException(status_code=400, detail="校验未通过，拒绝归档")

    staging = ensure_staging_dir(config)
    src = staging / filename
    _, date_str, _ = validate_filename(filename)
    year_dir = Path(config.paths.fnl_archive) / date_str[:4]
    year_dir.mkdir(parents=True, exist_ok=True)
    dst = year_dir / filename

    if dst.exists():
        dst.unlink()
    os.replace(src, dst)

    request_file = staging / f"{filename}.request.json"
    if request_file.exists():
        _update_repair_status(request_file, "completed")

    return FnlCompleteResult(
        filename=filename,
        archive_path=str(dst),
        message="已归档到补给目录",
    )


def _update_repair_status(request_file: Path, status: str) -> None:
    import json

    try:
        data = json.loads(request_file.read_text(encoding="utf-8"))
        data["status"] = status
        data["completed_at"] = datetime.now(timezone.utc).isoformat()
        request_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError):
        pass


def delete_staging_file(config: AppConfig, filename: str) -> dict:
    validate_filename(filename)
    staging = ensure_staging_dir(config)
    path = staging / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    path.unlink()
    (staging / f"{filename}.uploading").unlink(missing_ok=True)
    return {"filename": filename, "message": "已删除 staging 文件"}


def list_staging_files(config: AppConfig) -> list[dict]:
    staging = ensure_staging_dir(config)
    items = []
    for path in sorted(staging.glob("fnl_*.grib2")):
        stat = path.stat()
        items.append(
            {
                "filename": path.name,
                "size_bytes": stat.st_size,
                "mtime": stat.st_mtime,
                "has_request": (staging / f"{path.name}.request.json").exists(),
            }
        )
    return items
