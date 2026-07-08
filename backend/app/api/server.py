from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ..core.security import require_admin
from ..schemas.run_control import FlowResponse
from ..schemas.server_control import ServerConfigUpdate, ServerTickRequest
from ..services.server_client import server_client
from ..services.server_products import PRODUCT_ROOT_KEY

router = APIRouter(dependencies=[Depends(require_admin)])


def wrap(result, *, extra: dict | None = None) -> FlowResponse:
    data = {
        "source": result.source,
        "stale": result.stale,
        "error": result.error,
        "payload": result.data,
    }
    if extra:
        data.update(extra)
    return FlowResponse(ok=not result.stale, data=data)


@router.get("/health", response_model=FlowResponse)
def server_health():
    result = server_client.health()
    return wrap(result)


@router.get("/status", response_model=FlowResponse)
def server_status():
    result = server_client.daemon_status()
    return wrap(result)


@router.get("/config", response_model=FlowResponse)
def server_config():
    result = server_client.get_config()
    return FlowResponse(
        ok=not result.stale,
        data={
            "source": result.source,
            "stale": result.stale,
            "error": result.error,
            "config": result.data,
        },
    )


@router.put("/config", response_model=FlowResponse)
def update_server_config(payload: ServerConfigUpdate):
    body = payload.model_dump(exclude_none=True)
    if not body:
        return FlowResponse(ok=False, data={"message": "no fields to update"})
    result = server_client.update_config(body)
    return FlowResponse(
        ok=True,
        data={
            "source": result.source,
            "message": (result.data or {}).get("message"),
            "config": (result.data or {}).get("config"),
            "updated": body,
        },
    )


@router.get("/regions", response_model=FlowResponse)
def server_regions():
    result = server_client.get_regions()
    return FlowResponse(
        ok=not result.stale,
        data={
            "source": result.source,
            "stale": result.stale,
            "error": result.error,
            "regions": result.data or [],
        },
    )


@router.get("/slurm/jobs", response_model=FlowResponse)
def server_slurm_jobs():
    result = server_client.slurm_jobs()
    return wrap(result)


@router.post("/tick", response_model=FlowResponse)
def server_tick(
    force: bool = Query(default=False),
    start_date: str | None = Query(default=None, pattern=r"^\d{8}$"),
    season: str | None = Query(default=None),
):
    result = server_client.tick(force=force, start_date=start_date, season=season)
    return wrap(result)


@router.post("/forecast/submit", response_model=FlowResponse)
def submit_forecast(payload: ServerTickRequest):
    """保存区域/季节配置（如有）并触发 tick。"""
    from fastapi import HTTPException

    updated: dict = {}
    config_patch: dict = {}
    if payload.season:
        config_patch["season"] = payload.season
    if payload.regions:
        config_patch["regions"] = payload.regions
    if config_patch:
        server_client.update_config(config_patch)
        updated["config"] = config_patch

    try:
        result = server_client.tick(
            force=payload.force,
            start_date=payload.start_date,
            season=payload.season,
        )
    except HTTPException as exc:
        return FlowResponse(
            ok=False,
            data={
                "message": str(exc.detail),
                "updated": updated,
                "error": str(exc.detail),
                "tick": None,
            },
        )

    tick = result.data or {}
    message = "预报提交完成"
    if tick.get("messages"):
        message = "; ".join(tick["messages"][:3])
    return FlowResponse(
        ok=not result.stale,
        data={
            "source": result.source,
            "stale": result.stale,
            "error": result.error,
            "message": message,
            "updated": updated,
            "tick": tick,
        },
    )


@router.post("/schedule/enable", response_model=FlowResponse)
def enable_schedule():
    result = server_client.update_config({"schedule_enabled": True})
    return FlowResponse(ok=True, data={"schedule_enabled": True, "result": result.data})


@router.post("/schedule/disable", response_model=FlowResponse)
def disable_schedule():
    result = server_client.update_config({"schedule_enabled": False})
    return FlowResponse(ok=True, data={"schedule_enabled": False, "result": result.data})


@router.post("/reconcile", response_model=FlowResponse)
def server_reconcile():
    result = server_client.reconcile()
    return wrap(result)


@router.get("/files/roots", response_model=FlowResponse)
def server_file_roots():
    result = server_client.file_roots()
    return wrap(result)


@router.get("/files/list/{root_key}", response_model=FlowResponse)
def server_file_list(root_key: str, path: str = Query(default="")):
    try:
        entries = server_client.list_directory(root_key, path)
    except HTTPException as exc:
        return FlowResponse(ok=False, data={"message": str(exc.detail), "entries": []})
    return FlowResponse(ok=True, data={"entries": entries, "root_key": root_key, "path": path})


@router.get("/files/tree/{root_key}", response_model=FlowResponse)
def server_file_tree(
    root_key: str,
    path: str = Query(default=""),
    depth: int = Query(default=3, ge=0, le=5),
):
    try:
        tree = server_client.file_tree(root_key, path, depth=depth)
    except HTTPException as exc:
        return FlowResponse(ok=False, data={"message": str(exc.detail)})
    return FlowResponse(ok=True, data={"tree": tree, "root_key": root_key, "path": path})


@router.get("/files/download/{root_key}")
def server_file_download(root_key: str, path: str = Query(...)):
    if root_key != PRODUCT_ROOT_KEY and root_key not in {"output", "runs", "logs", "project", "fnl"}:
        raise HTTPException(status_code=400, detail=f"不支持的根目录: {root_key}")
    content = server_client.download_file(root_key, path)
    filename = path.replace("\\", "/").split("/")[-1]
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
