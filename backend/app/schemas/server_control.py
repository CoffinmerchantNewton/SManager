from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ServerConfigUpdate(BaseModel):
    schedule_enabled: Optional[bool] = None
    tick_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    repair_deadline: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    regions: Optional[list[str]] = None
    season: Optional[str] = None
    pre: Optional[str] = None
    fnl_gfs_default: Optional[int] = Field(default=None, ge=0, le=3)
    fnl_gfs_fallback: Optional[int] = Field(default=None, ge=0, le=3)


class ServerTickRequest(BaseModel):
    force: bool = False
    start_date: Optional[str] = Field(default=None, pattern=r"^\d{8}$")
    season: Optional[str] = None
    regions: Optional[list[str]] = None
