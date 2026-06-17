"""普通用户态定时调度。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from config_manager import load_config, save_config
from models import AppConfig
from run_manager import beijing_today, get_daemon_state, reconcile, run_tick
from tianqing_service import maybe_run_tianqing_download

logger = logging.getLogger("smanager.scheduler")


class ForecastScheduler:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None
        self._last_tick_date: Optional[str] = None

    @property
    def started_at(self) -> Optional[datetime]:
        return self._started_at

    async def start(self) -> None:
        if self._task is not None:
            return
        self._started_at = datetime.now()
        self._task = asyncio.create_task(self._loop(), name="forecast-scheduler")
        logger.info("scheduler started")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("scheduler stopped")

    async def _loop(self) -> None:
        while True:
            try:
                config = load_config()
                if config.schedule.enabled:
                    await self._maybe_tick(config)
                await asyncio.to_thread(maybe_run_tianqing_download, config)
                await asyncio.to_thread(reconcile, config)
                await asyncio.sleep(max(10, config.schedule.poll_interval))
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("scheduler loop error")
                await asyncio.sleep(30)

    async def _maybe_tick(self, config: AppConfig) -> None:
        tz = ZoneInfo(config.schedule.timezone)
        now = datetime.now(tz)
        today = now.strftime("%Y%m%d")

        if self._last_tick_date == today:
            return

        state = get_daemon_state()
        last_detail = state.get("last_tick_detail") or {}
        if last_detail.get("date") == today and last_detail.get("regions_submitted"):
            self._last_tick_date = today
            return

        parts = config.schedule.tick_time.split(":")
        if len(parts) != 2:
            return
        hour, minute = int(parts[0]), int(parts[1])
        tick_moment = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now < tick_moment:
            return

        logger.info("auto tick for %s", today)
        await asyncio.to_thread(run_tick, config, False, today)
        self._last_tick_date = today

    def next_tick_at(self, config: AppConfig) -> Optional[str]:
        if not config.schedule.enabled:
            return None
        tz = ZoneInfo(config.schedule.timezone)
        now = datetime.now(tz)
        parts = config.schedule.tick_time.split(":")
        if len(parts) != 2:
            return None
        hour, minute = int(parts[0]), int(parts[1])
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= candidate:
            candidate += timedelta(days=1)
        return candidate.isoformat()


scheduler = ForecastScheduler()
