from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status

from ..schemas.run_control import FnlRepairRequest, FnlVerifyRequest, FlowResponse
from ..services.fnl_downloader import build_gdex_url, ensure_local_file, parse_fnl_filename
from ..services.fnl_repair import repair_one, repair_pending
from ..services.server_client import server_client

router = APIRouter()


def _repair_to_file(record: dict) -> dict:
    filename = record.get("filename") or ""
    valid_time = ""
    if filename.startswith("fnl_") and filename.endswith(".grib2"):
        parts = filename.removeprefix("fnl_").removesuffix(".grib2").split("_")
        if len(parts) >= 2:
            valid_time = f"{parts[0]}{parts[1]}"
    status_value = record.get("status") or "pending"
    return {
        "valid_time": valid_time,
        "file_name": filename,
        "status": status_value,
        "needs_repair": status_value in {"pending", "expired"},
        "source": "repair_request",
        "server_path": None,
        "local_path": None,
        "size_bytes": None,
        "valid_grib": status_value in {"verified", "completed"},
        "uploaded": status_value in {"uploaded", "verified", "completed"},
        "repair_attempt": 0,
        "error_message": None,
        "checked_at": record.get("requested_at"),
        "region": record.get("region"),
        "date": record.get("date"),
        "hour": record.get("hour"),
    }


def _scan_to_files(scan: dict) -> list[dict]:
    missing = scan.get("missing") or []
    files: list[dict] = []
    for name in missing:
        files.append(
            {
                "valid_time": "",
                "file_name": name,
                "status": "missing",
                "needs_repair": True,
                "source": "fnl_scan",
                "server_path": None,
                "local_path": None,
                "size_bytes": None,
                "valid_grib": False,
                "uploaded": False,
                "gdex_url": build_gdex_url(name),
            }
        )
    return files


def _resolve_repair_targets(payload: FnlRepairRequest) -> list[str]:
    if payload.filenames:
        return list(payload.filenames)

    repairs = server_client.repair_requests(status="pending")
    pending = repairs.data or []
    if pending:
        return [str(item["filename"]) for item in pending if item.get("filename")]

    if payload.start or payload.run_id:
        start_date = _resolve_start_date(payload)
        scan = server_client.fnl_scan(start_date).data or {}
        return list(scan.get("missing") or [])

    return []


@router.post("/verify-server", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def verify_server_fnl(payload: FnlVerifyRequest):
    start_date = _resolve_start_date(payload)
    result = server_client.fnl_scan(start_date)
    scan = result.data or {}
    files = _scan_to_files(scan)
    return FlowResponse(
        ok=not result.stale and not scan.get("missing"),
        data={
            "files": files,
            "scan": scan,
            "source": result.source,
            "stale": result.stale,
            "error": result.error,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.post("/repair", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def repair_fnl(payload: FnlRepairRequest):
    if not server_client.configured:
        raise HTTPException(status_code=503, detail="SERVER_API_BASE_URL is not configured")

    targets = _resolve_repair_targets(payload)
    if not targets:
        return FlowResponse(
            ok=True,
            data={
                "message": "no pending FNL repair targets",
                "total": 0,
                "success": 0,
                "failed": 0,
                "results": [],
            },
        )

    repairs = server_client.repair_requests(status="pending")
    summary = repair_pending(
        targets,
        dry_run=payload.dry_run,
        use_cache=payload.use_cache,
        pending_requests=repairs.data or [],
    )
    return FlowResponse(
        ok=summary["failed"] == 0,
        data={
            "message": "FNL repair finished",
            "requested": payload.model_dump(),
            **summary,
        },
    )


@router.post("/repair/{filename}", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def repair_single_fnl(
    filename: str,
    dry_run: bool = Query(default=False),
    use_cache: bool = Query(default=True),
):
    if not server_client.configured:
        raise HTTPException(status_code=503, detail="SERVER_API_BASE_URL is not configured")
    try:
        parse_fnl_filename(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = repair_one(filename, dry_run=dry_run, use_cache=use_cache)
    return FlowResponse(ok=bool(result.get("ok")), data=result)


@router.post("/download/{filename}", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def download_fnl_only(filename: str, use_cache: bool = Query(default=True)):
    try:
        parse_fnl_filename(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ok, message, local_path, meta = ensure_local_file(filename, use_cache=use_cache)
    return FlowResponse(
        ok=ok,
        data={
            "filename": filename,
            "local_path": str(local_path) if local_path else None,
            "message": message,
            "gdex_url": meta.get("url"),
            **meta,
        },
    )


@router.get("/coverage", response_model=FlowResponse)
def fnl_coverage(
    start: str | None = None,
    end: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    needs_repair: bool | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
):
    if not server_client.configured:
        return FlowResponse(
            ok=False,
            data={"code": "server_first_migration_pending", "message": "SERVER_API_BASE_URL 未配置", "files": []},
        )

    files: list[dict] = []
    scan = None
    scan_result = None
    if start:
        start_date = start[:8]
        scan_result = server_client.fnl_scan(start_date)
        scan = scan_result.data
        files.extend(_scan_to_files(scan or {}))

    repair_result = server_client.repair_requests()
    for item in repair_result.data or []:
        record = _repair_to_file(item)
        filename = record.get("file_name") or ""
        if filename:
            try:
                record["gdex_url"] = build_gdex_url(filename)
            except ValueError:
                pass
        files.append(record)

    staging_result = server_client.fnl_staging()
    for item in staging_result.data or []:
        if isinstance(item, dict):
            files.append(
                {
                    "valid_time": "",
                    "file_name": item.get("filename") or item.get("name") or "",
                    "status": "staging",
                    "needs_repair": False,
                    "source": "staging",
                    "server_path": item.get("path"),
                    "size_bytes": item.get("size_bytes") or item.get("size"),
                    "valid_grib": False,
                    "uploaded": True,
                }
            )

    if status_filter:
        files = [item for item in files if item.get("status") == status_filter]
    if needs_repair is True:
        files = [item for item in files if item.get("needs_repair")]
    elif needs_repair is False:
        files = [item for item in files if not item.get("needs_repair")]

    files = files[:limit]
    return FlowResponse(
        ok=True,
        data={
            "files": files,
            "scan": scan,
            "source": "server",
            "repair_source": repair_result.source,
            "stale": bool(
                (scan_result.error if scan_result else False)
                or repair_result.error
                or staging_result.error
            ),
            "error": scan_result.error if scan_result else repair_result.error or staging_result.error,
        },
    )


@router.get("/repair-requests", response_model=FlowResponse)
def list_repair_requests(status: str | None = Query(default=None)):
    result = server_client.repair_requests(status=status)
    return FlowResponse(
        ok=not result.stale,
        data={
            "requests": result.data or [],
            "source": result.source,
            "stale": result.stale,
            "error": result.error,
        },
    )


def _resolve_start_date(payload: FnlVerifyRequest) -> str:
    if payload.start:
        return payload.start[:8]
    if payload.run_id:
        return payload.run_id[:8]
    raise HTTPException(status_code=400, detail="run_id or start is required")
