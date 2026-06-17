from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..core.config import settings
from .fnl_downloader import ensure_local_file, parse_fnl_filename

logger = logging.getLogger(__name__)


def _auth_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if settings.SERVER_API_TOKEN:
        headers["Authorization"] = f"Bearer {settings.SERVER_API_TOKEN}"
    return headers


def _read_json_response(response) -> Any:
    raw = response.read().decode("utf-8")
    if not raw:
        return None
    return json.loads(raw)


def _server_url(path: str, params: dict[str, Any] | None = None) -> str:
    base = (settings.SERVER_API_BASE_URL or "").rstrip("/")
    query = f"?{urlencode(params)}" if params else ""
    return f"{base}{path}{query}"


def upload_fnl_post(local_path: Path, filename: str | None = None) -> dict[str, Any]:
    if not settings.SERVER_API_BASE_URL:
        raise RuntimeError("SERVER_API_BASE_URL is not configured")
    upload_name = filename or local_path.name
    boundary = uuid.uuid4().hex
    file_bytes = local_path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{upload_name}"\r\n'.encode(),
            b"Content-Type: application/octet-stream\r\n\r\n",
            file_bytes,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    headers = _auth_headers()
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    request = Request(
        _server_url("/api/fnl/upload"),
        data=body,
        headers=headers,
        method="POST",
    )
    timeout = settings.FNL_UPLOAD_TIMEOUT
    try:
        with urlopen(request, timeout=timeout) as response:
            data = _read_json_response(response)
            return data if isinstance(data, dict) else {"result": data}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(detail or exc.reason) from exc
    except URLError as exc:
        raise RuntimeError(f"upload failed: {exc.reason}") from exc


def verify_fnl_post(filename: str) -> dict[str, Any]:
    request = Request(
        _server_url(f"/api/fnl/verify/{filename}"),
        headers=_auth_headers(),
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            data = _read_json_response(response)
            return data if isinstance(data, dict) else {"result": data}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(detail or exc.reason) from exc


def complete_fnl_post(filename: str, *, force: bool = False) -> dict[str, Any]:
    params = {"force": "true"} if force else None
    request = Request(
        _server_url(f"/api/fnl/complete/{filename}", params),
        headers=_auth_headers(),
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            data = _read_json_response(response)
            return data if isinstance(data, dict) else {"result": data}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(detail or exc.reason) from exc


def repair_one(filename: str, *, dry_run: bool = False, use_cache: bool = True) -> dict[str, Any]:
    parse_fnl_filename(filename)
    result: dict[str, Any] = {"filename": filename, "ok": False, "steps": []}

    if dry_run:
        result["ok"] = True
        result["steps"].append({"step": "plan", "status": "dry_run"})
        return result

    ok, message, local_path, meta = ensure_local_file(filename, use_cache=use_cache)
    result["steps"].append({"step": "download", "ok": ok, "message": message, **meta})
    if not ok or local_path is None:
        result["error"] = message
        return result

    try:
        upload = upload_fnl_post(local_path, filename)
        result["steps"].append({"step": "upload", "ok": True, "response": upload})
    except RuntimeError as exc:
        result["steps"].append({"step": "upload", "ok": False, "message": str(exc)})
        result["error"] = str(exc)
        return result

    try:
        verify = verify_fnl_post(filename)
        valid = bool(verify.get("valid"))
        result["steps"].append({"step": "verify", "ok": valid, "response": verify})
        if not valid:
            result["error"] = verify.get("message") or "server verify failed"
            return result
    except RuntimeError as exc:
        result["steps"].append({"step": "verify", "ok": False, "message": str(exc)})
        result["error"] = str(exc)
        return result

    try:
        complete = complete_fnl_post(filename)
        result["steps"].append({"step": "complete", "ok": True, "response": complete})
        result["ok"] = True
        result["archive_path"] = complete.get("archive_path")
        return result
    except RuntimeError as exc:
        result["steps"].append({"step": "complete", "ok": False, "message": str(exc)})
        result["error"] = str(exc)
        return result


def repair_pending(
    filenames: list[str] | None = None,
    *,
    dry_run: bool = False,
    use_cache: bool = True,
    pending_requests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    targets = list(filenames or [])
    if not targets and pending_requests:
        targets = [
            str(item.get("filename"))
            for item in pending_requests
            if item.get("status") in {None, "pending", "expired"} and item.get("filename")
        ]

    results = [repair_one(name, dry_run=dry_run, use_cache=use_cache) for name in targets]
    success = sum(1 for item in results if item.get("ok"))
    return {
        "total": len(results),
        "success": success,
        "failed": len(results) - success,
        "results": results,
    }
