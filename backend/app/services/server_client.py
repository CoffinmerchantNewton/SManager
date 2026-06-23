from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from ..core.config import settings
from .server_cache import read_cache, write_cache

logger = logging.getLogger(__name__)


@dataclass
class ServerResult:
    data: Any
    source: str
    stale: bool = False
    error: str | None = None


class ServerClient:
    def __init__(self) -> None:
        self.base_url = (settings.SERVER_API_BASE_URL or "").rstrip("/")
        self.token = settings.SERVER_API_TOKEN or ""

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _encode_params(self, params: dict[str, Any] | None) -> str:
        if not params:
            return ""
        filtered: dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, bool):
                filtered[key] = "true" if value else "false"
            else:
                filtered[key] = value
        if not filtered:
            return ""
        return "?" + urllib.parse.urlencode(filtered)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        if not self.configured:
            raise HTTPException(status_code=503, detail="SERVER_API_BASE_URL is not configured")

        query = self._encode_params(params)
        effective_timeout = timeout if timeout is not None else float(settings.SERVER_REQUEST_TIMEOUT)

        url = f"{self.base_url}{path}{query}"
        payload = None
        headers = self._headers()
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=payload, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=effective_timeout) as response:
                raw = response.read().decode("utf-8")
                if not raw:
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HTTPException(status_code=exc.code, detail=detail or exc.reason) from exc
        except TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail=f"smanager-server 响应超时（>{effective_timeout:.0f}s），任务可能仍在服务器上执行",
            ) from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError):
                raise HTTPException(
                    status_code=504,
                    detail=f"smanager-server 响应超时（>{effective_timeout:.0f}s），任务可能仍在服务器上执行",
                ) from exc
            raise HTTPException(status_code=502, detail=f"Server unreachable: {reason}") from exc
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail="Invalid JSON from smanager-server") from exc

    def fetch(
        self,
        cache_name: str,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ServerResult:
        try:
            data = self._request(method, path, params=params, body=body, timeout=timeout)
            write_cache(cache_name, data)
            return ServerResult(data=data, source="server")
        except HTTPException as exc:
            cached = read_cache(cache_name)
            if cached is not None:
                return ServerResult(
                    data=cached.get("payload"),
                    source="cache",
                    stale=True,
                    error=str(exc.detail),
                )
            raise

    def get(self, cache_name: str, path: str, *, params: dict[str, Any] | None = None) -> ServerResult:
        return self.fetch(cache_name, "GET", path, params=params)

    def post(
        self,
        cache_name: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ServerResult:
        return self.fetch(cache_name, "POST", path, params=params, timeout=timeout)

    def health(self) -> ServerResult:
        return self.get("server_health", "/health")

    def daemon_status(self) -> ServerResult:
        return self.get("server_daemon_status", "/api/status")

    def list_runs(self, limit: int = 50, *, live: bool = True, prefer_cache: bool = False) -> ServerResult:
        cached = read_cache("server_runs")
        if prefer_cache and cached is not None:
            return ServerResult(data=cached.get("payload"), source="cache", stale=False)

        if live:
            try:
                data = self._request(
                    "GET",
                    "/api/runs",
                    params={"limit": limit},
                    timeout=float(settings.SERVER_RUNS_REQUEST_TIMEOUT),
                )
                write_cache("server_runs", data)
                return ServerResult(data=data, source="server")
            except HTTPException as exc:
                if cached is not None:
                    return ServerResult(
                        data=cached.get("payload"),
                        source="cache",
                        stale=True,
                        error=str(exc.detail),
                    )
                raise
        return self.get("server_runs", "/api/runs", params={"limit": limit})

    def refresh_runs_cache(self, limit: int = 50) -> None:
        try:
            self.list_runs(limit=limit, live=True)
        except HTTPException:
            logger.warning("background runs cache refresh failed", exc_info=True)

    def run_detail(self, season: str, region: str, run_id: str) -> ServerResult:
        cache_name = f"server_run_{season}_{region}_{run_id}"
        return self.get(cache_name, f"/api/runs/{season}/{region}/{run_id}")

    def slurm_jobs(self) -> ServerResult:
        return self.get("server_slurm_jobs", "/api/slurm/jobs")

    def repair_requests(self, status: str | None = None) -> ServerResult:
        return self.get("server_repair_requests", "/api/repair-requests", params={"status": status})

    def fnl_staging(self) -> ServerResult:
        return self.get("server_fnl_staging", "/api/fnl/staging")

    def tail_file(self, root_key: str, path: str, lines: int = 120, *, live: bool = True) -> ServerResult:
        cache_name = f"server_tail_{root_key}_{path.replace('/', '_')}"
        if live:
            try:
                data = self._request("GET", f"/api/files/tail/{root_key}", params={"path": path, "lines": lines})
                return ServerResult(data=data, source="server")
            except HTTPException as exc:
                return ServerResult(data=None, source="server", stale=False, error=str(exc.detail))
        return self.get(cache_name, f"/api/files/tail/{root_key}", params={"path": path, "lines": lines})

    def run_detail_live(self, season: str, region: str, run_id: str) -> ServerResult:
        try:
            data = self._request("GET", f"/api/runs/{season}/{region}/{run_id}")
            write_cache(f"server_run_{season}_{region}_{run_id}", data)
            return ServerResult(data=data, source="server")
        except HTTPException as exc:
            cache_name = f"server_run_{season}_{region}_{run_id}"
            cached = read_cache(cache_name)
            if cached is not None:
                return ServerResult(
                    data=cached.get("payload"),
                    source="cache",
                    stale=True,
                    error=str(exc.detail),
                )
            raise

    def put_live(self, path: str, body: dict[str, Any]) -> ServerResult:
        try:
            data = self._request("PUT", path, body=body)
            return ServerResult(data=data, source="server")
        except HTTPException as exc:
            raise exc

    def get_config(self) -> ServerResult:
        return self.get("server_config", "/api/config")

    def update_config(self, body: dict[str, Any]) -> ServerResult:
        data = self._request("PUT", "/api/config", body=body)
        cached = data.get("config") if isinstance(data, dict) else data
        if cached is not None:
            write_cache("server_config", cached)
        return ServerResult(data=data, source="server")

    def get_regions(self) -> ServerResult:
        return self.get("server_regions", "/api/regions")

    def tick(
        self,
        *,
        force: bool = False,
        start_date: str | None = None,
        season: str | None = None,
    ) -> ServerResult:
        params: dict[str, Any] = {"force": force}
        if start_date:
            params["start_date"] = start_date
        if season:
            params["season"] = season
        return self.post(
            "server_last_tick",
            "/api/tick",
            params=params,
            timeout=float(settings.SERVER_TICK_TIMEOUT),
        )

    def fnl_scan(self, start_date: str, season: str | None = None) -> ServerResult:
        params: dict[str, Any] = {"start_date": start_date}
        if season:
            params["season"] = season
        cache_name = f"server_fnl_scan_{start_date}_{season or 'auto'}"
        return self.get(cache_name, "/api/fnl/scan", params=params)

    def reconcile(self) -> ServerResult:
        return self.post("server_last_reconcile", "/api/reconcile")


server_client = ServerClient()
