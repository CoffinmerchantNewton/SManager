from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..core.security import require_admin
from ..schemas.run_control import FlowResponse
from ..schemas.server_control import ServerConfigUpdate, ServerTickRequest
from ..services.server_client import server_client

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
