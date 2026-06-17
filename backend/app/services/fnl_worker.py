from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ..core.config import settings
from .fnl_repair import repair_pending
from .server_client import server_client

logger = logging.getLogger("smanager.fnl_worker")

_worker_task: Optional[asyncio.Task] = None


async def _poll_once() -> None:
    if not server_client.configured:
        return
    try:
        repairs = await asyncio.to_thread(lambda: server_client.repair_requests(status="pending"))
        pending = repairs.data or []
        if not pending:
            return
        filenames = [item.get("filename") for item in pending if item.get("filename")]
        if not filenames:
            return
        logger.info("FNL worker repairing %d pending file(s)", len(filenames))
        summary = await asyncio.to_thread(
            repair_pending,
            filenames=filenames,
            dry_run=False,
            use_cache=True,
            pending_requests=pending,
        )
        logger.info(
            "FNL worker done: success=%s failed=%s total=%s",
            summary.get("success"),
            summary.get("failed"),
            summary.get("total"),
        )
    except Exception:
        logger.exception("FNL worker poll failed")


async def _loop(interval: int) -> None:
    while True:
        await _poll_once()
        await asyncio.sleep(interval)


async def start_fnl_worker() -> None:
    global _worker_task
    interval = settings.FNL_REPAIR_POLL_INTERVAL_SECONDS
    if interval <= 0 or not server_client.configured:
        return
    if _worker_task is not None:
        return
    _worker_task = asyncio.create_task(_loop(interval), name="fnl-repair-worker")
    logger.info("FNL repair worker started (interval=%ss)", interval)


async def stop_fnl_worker() -> None:
    global _worker_task
    if _worker_task is None:
        return
    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass
    _worker_task = None
    logger.info("FNL repair worker stopped")
