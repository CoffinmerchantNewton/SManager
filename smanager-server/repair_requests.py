"""FNL repair request 状态机。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from file_tree import ensure_staging_dir
from models import AppConfig, RepairRequest


def _request_path(staging: Path, filename: str) -> Path:
    return staging / f"{filename}.request.json"


def create_repair_request(
    config: AppConfig,
    filename: str,
    region: str,
    tz_name: str = "Asia/Shanghai",
) -> RepairRequest:
    staging = ensure_staging_dir(config)
    path = _request_path(staging, filename)
    date_str = filename[4:12]
    hour = filename[13:15]
    now = datetime.now(ZoneInfo(tz_name))
    payload = {
        "filename": filename,
        "date": date_str,
        "hour": hour,
        "requested_at": now.isoformat(),
        "region": region,
        "status": "pending",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return RepairRequest(**payload)


def list_repair_requests(config: AppConfig, status: Optional[str] = None) -> list[RepairRequest]:
    staging = ensure_staging_dir(config)
    results: list[RepairRequest] = []
    for path in sorted(staging.glob("fnl_*.grib2.request.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            req = RepairRequest(**data)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        if status and req.status != status:
            continue
        results.append(req)
    return results


def get_repair_request(config: AppConfig, filename: str) -> RepairRequest:
    staging = ensure_staging_dir(config)
    path = _request_path(staging, filename)
    if not path.exists():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="repair request 不存在")
    data = json.loads(path.read_text(encoding="utf-8"))
    return RepairRequest(**data)


def mark_repair_uploaded(config: AppConfig, filename: str) -> RepairRequest:
    staging = ensure_staging_dir(config)
    path = _request_path(staging, filename)
    if not path.exists():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="repair request 不存在")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = "uploaded"
    data["uploaded_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return RepairRequest(**data)
