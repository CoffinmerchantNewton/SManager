"""SManager 服务器 FastAPI 入口。"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from config_manager import apply_config_update, load_config, save_config  # noqa: E402
from file_tree import (  # noqa: E402
    build_tree,
    list_directory,
    resolve_download_path,
    tail_log_file,
)
from fnl_service import (  # noqa: E402
    complete_upload,
    delete_staging_file,
    list_staging_files,
    save_upload,
    verify_staging_file,
)
from models import (  # noqa: E402
    ConfigUpdate,
    DaemonStatus,
    FnlScanResult,
    HealthResponse,
    RegionInfo,
    RepairRequest,
    RunSummary,
    TickResult,
)
from repair_requests import (  # noqa: E402
    get_repair_request,
    list_repair_requests,
    mark_repair_uploaded,
)
from run_manager import (  # noqa: E402
    beijing_today,
    get_daemon_state,
    get_run_detail,
    list_runs,
    reconcile,
    resolve_season_for_date,
    run_tick,
    scan_fnl_for_date,
    query_slurm_jobs,
)
from scheduler import scheduler  # noqa: E402
from tianqing_service import next_tianqing_attempt_at  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("smanager.server")

_START_TIME = time.time()
_VERSION = "0.1.0"


def _check_token(authorization: Optional[str] = Header(default=None)) -> None:
    config = load_config()
    token = config.server.api_token
    if not token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="需要 Bearer token")
    if authorization.removeprefix("Bearer ").strip() != token:
        raise HTTPException(status_code=403, detail="token 无效")


Auth = Annotated[None, Depends(_check_token)]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config = load_config()
    await scheduler.start()
    logger.info(
        "smanager-server 已启动 (port=%s, schedule=%s)",
        config.server.port,
        config.schedule.enabled,
    )
    yield
    await scheduler.stop()
    logger.info("smanager-server 已停止")


app = FastAPI(
    title="SManager Server",
    description="花粉预报服务器控制面 API",
    version=_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 健康与状态
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    config = load_config()
    return HealthResponse(
        status="ok",
        version=_VERSION,
        uptime_seconds=time.time() - _START_TIME,
        schedule_enabled=config.schedule.enabled,
    )


@app.get("/api/status", response_model=DaemonStatus, tags=["system"])
def api_status(_: Auth) -> DaemonStatus:
    config = load_config()
    state = get_daemon_state()
    tz = ZoneInfo(config.schedule.timezone)
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now(tz)
    repairs = list_repair_requests(config, status="pending")
    runs = list_runs(config, limit=100)
    return DaemonStatus(
        started_at=scheduler.started_at.isoformat() if scheduler.started_at else "",
        schedule_enabled=config.schedule.enabled,
        tianqing_enabled=config.tianqing.enabled,
        last_tick_at=state.get("last_tick_at"),
        last_tick_result=state.get("last_tick_result"),
        next_tick_at=scheduler.next_tick_at(config),
        tianqing_done_date=state.get("tianqing_done_date"),
        tianqing_last_attempt_at=state.get("tianqing_last_attempt_at"),
        tianqing_last_result=state.get("tianqing_last_result"),
        tianqing_next_attempt_at=next_tianqing_attempt_at(config),
        last_reconcile_at=state.get("last_reconcile_at"),
        active_runs=len(runs),
        pending_repairs=len(repairs),
        server_time_utc=now_utc.isoformat(),
        server_time_local=now_local.isoformat(),
    )


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------


@app.get("/api/config", tags=["config"])
def get_config(_: Auth):
    return load_config().model_dump()


@app.put("/api/config", tags=["config"])
def update_config(body: ConfigUpdate, _: Auth):
    config = load_config()
    config = apply_config_update(config, body)
    save_config(config)
    return {"message": "配置已保存", "config": config.model_dump()}


@app.get("/api/regions", response_model=list[RegionInfo], tags=["config"])
def api_regions(_: Auth):
    config = load_config()
    root = Path(config.paths.project_root)
    sys.path.insert(0, str(root))
    from config.registry import REGIONS  # noqa: WPS433

    today = beijing_today(config)
    season = resolve_season_for_date(today) or config.forecast.season
    items: list[RegionInfo] = []
    for key, profile in REGIONS.items():
        if season and season not in profile.templates:
            continue
        items.append(
            RegionInfo(
                region=key,
                display_name=profile.display_name,
                seasons=list(profile.templates.keys()),
                slurm_code=profile.slurm_code,
            )
        )
    return items


# ---------------------------------------------------------------------------
# 调度与 Run
# ---------------------------------------------------------------------------


@app.post("/api/tick", response_model=TickResult, tags=["scheduler"])
async def api_tick(
    _: Auth,
    force: bool = Query(False, description="忽略已有 run / FNL 等待"),
    start_date: Optional[str] = Query(None, pattern=r"^\d{8}$"),
    season: Optional[str] = Query(None, description="手动指定季节 spring/autumn，默认按月份自动"),
):
    config = load_config()
    return await asyncio.to_thread(run_tick, config, force, start_date, season)


@app.post("/api/reconcile", tags=["scheduler"])
async def api_reconcile(_: Auth):
    config = load_config()
    return await asyncio.to_thread(reconcile, config)


@app.get("/api/runs", response_model=list[RunSummary], tags=["runs"])
def api_runs(_: Auth, limit: int = Query(30, ge=1, le=200)):
    return list_runs(load_config(), limit=limit)


@app.get("/api/runs/{season}/{region}/{run_id}", response_model=RunSummary, tags=["runs"])
def api_run_detail(season: str, region: str, run_id: str, _: Auth):
    return get_run_detail(load_config(), season, region, run_id)


@app.get("/api/slurm/jobs", tags=["runs"])
def api_slurm_jobs(_: Auth):
    return query_slurm_jobs()


# ---------------------------------------------------------------------------
# FNL
# ---------------------------------------------------------------------------


@app.get("/api/fnl/scan", response_model=FnlScanResult, tags=["fnl"])
def api_fnl_scan(
    _: Auth,
    start_date: str = Query(..., pattern=r"^\d{8}$"),
    season: Optional[str] = Query(None, description="默认按 start_date 月份自动推断"),
):
    config = load_config()
    effective_season = season or resolve_season_for_date(start_date) or config.forecast.season
    return scan_fnl_for_date(config, start_date, effective_season)


@app.get("/api/fnl/staging", tags=["fnl"])
def api_fnl_staging(_: Auth):
    return list_staging_files(load_config())


@app.post("/api/fnl/upload", tags=["fnl"])
async def api_fnl_upload(_: Auth, file: UploadFile = File(...)):
    config = load_config()
    result = await save_upload(config, file)
    try:
        mark_repair_uploaded(config, result.filename)
    except HTTPException:
        pass
    return result


@app.post("/api/fnl/verify/{filename}", tags=["fnl"])
def api_fnl_verify(filename: str, _: Auth):
    return verify_staging_file(load_config(), filename)


@app.post("/api/fnl/complete/{filename}", tags=["fnl"])
def api_fnl_complete(filename: str, _: Auth, force: bool = Query(False)):
    return complete_upload(load_config(), filename, force=force)


@app.delete("/api/fnl/staging/{filename}", tags=["fnl"])
def api_fnl_delete(filename: str, _: Auth):
    return delete_staging_file(load_config(), filename)


# ---------------------------------------------------------------------------
# Repair requests
# ---------------------------------------------------------------------------


@app.get("/api/repair-requests", response_model=list[RepairRequest], tags=["repair"])
def api_repair_list(_: Auth, status: Optional[str] = Query(None)):
    return list_repair_requests(load_config(), status=status)


@app.get("/api/repair-requests/{filename}", response_model=RepairRequest, tags=["repair"])
def api_repair_detail(filename: str, _: Auth):
    return get_repair_request(load_config(), filename)


# ---------------------------------------------------------------------------
# 文件树
# ---------------------------------------------------------------------------


@app.get("/api/files/roots", tags=["files"])
def api_file_roots(_: Auth):
    config = load_config()
    return {
        key: {"label": spec.label, "path": spec.path, "writable": spec.writable}
        for key, spec in config.file_tree.roots.items()
    }


@app.get("/api/files/tree/{root_key}", tags=["files"])
def api_file_tree(
    root_key: str,
    _: Auth,
    path: str = Query("", description="相对根目录的子路径"),
    depth: int = Query(2, ge=0, le=5),
):
    return build_tree(load_config(), root_key, path, depth=depth)


@app.get("/api/files/list/{root_key}", tags=["files"])
def api_file_list(
    root_key: str,
    _: Auth,
    path: str = Query(""),
):
    return list_directory(load_config(), root_key, path)


@app.get("/api/files/download/{root_key}", tags=["files"])
def api_file_download(
    root_key: str,
    _: Auth,
    path: str = Query(..., description="相对根目录的文件路径"),
):
    config = load_config()
    file_path = resolve_download_path(config, root_key, path)
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@app.get("/api/files/tail/{root_key}", tags=["files"])
def api_file_tail(
    root_key: str,
    _: Auth,
    path: str = Query(...),
    lines: int = Query(100, ge=1, le=2000),
):
    content, truncated = tail_log_file(load_config(), root_key, path, lines=lines)
    return {"path": path, "lines": content, "truncated": truncated}


def main() -> None:
    import uvicorn

    config = load_config()
    uvicorn.run(
        "serverd:app",
        host=config.server.host,
        port=config.server.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
