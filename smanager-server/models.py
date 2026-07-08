"""Pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class FileTreeRoot(BaseModel):
    path: str
    label: str
    writable: bool = False


class FileTreeRootsConfig(BaseModel):
    roots: dict[str, FileTreeRoot] = Field(default_factory=dict)


class PathsConfig(BaseModel):
    project_root: str
    fnl_staging: str
    fnl_archive: str
    wgrib2: str
    fnl_min_mb: float = 5.0


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8765
    api_token: str = ""


class ScheduleConfig(BaseModel):
    enabled: bool = True
    tick_time: str = "07:30"
    timezone: str = "Asia/Shanghai"
    repair_deadline: str = "07:50"
    poll_interval: int = 60


class TianqingConfig(BaseModel):
    enabled: bool = True
    start_time: str = "02:00"
    timezone: str = "Asia/Shanghai"
    script_path: str = (
        "/g7/anxq/Zhangjt/workspace/auto-pollen-lijt/"
        "Tianqing_data_download/music-sdk-scriptFile-v2.0/download_dates.sh"
    )
    data_dir: str = (
        "/g7/anxq/Zhangjt/workspace/pollen_emission/Mete_Data/Tianqing_TEM_Avg_download"
    )
    min_lines: int = 100
    timeout_seconds: int = 3600


class ForecastConfig(BaseModel):
    season: str = "autumn"
    pre: str = "pre7"
    regions: list[str] = Field(default_factory=lambda: ["Beijing", "InnerMG", "Shaanxi", "Yulin", "China"])
    fnl_gfs_default: int = 2
    fnl_gfs_fallback: int = 1
    task_dup_action: Literal["continue", "overwrite", "new"] = "continue"
    # InnerMG 秋季：standard=仅标准版 | caoditu=仅草地TIF | both=两个都跑
    innermg_autumn_variant: Literal["standard", "caoditu", "both"] = "both"


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    tianqing: TianqingConfig = Field(default_factory=TianqingConfig)
    forecast: ForecastConfig = Field(default_factory=ForecastConfig)
    paths: PathsConfig
    file_tree: FileTreeRootsConfig = Field(default_factory=FileTreeRootsConfig)


class ConfigUpdate(BaseModel):
    """允许通过 API 部分更新的配置字段。"""

    schedule_enabled: Optional[bool] = None
    tianqing_enabled: Optional[bool] = None
    tick_time: Optional[str] = None
    repair_deadline: Optional[str] = None
    regions: Optional[List[str]] = None
    season: Optional[str] = None
    pre: Optional[str] = None
    fnl_gfs_default: Optional[int] = None
    fnl_gfs_fallback: Optional[int] = None
    innermg_autumn_variant: Optional[Literal["standard", "caoditu", "both"]] = None


class TreeNode(BaseModel):
    name: str
    path: str
    type: Literal["file", "directory"]
    size: Optional[int] = None
    mtime: Optional[float] = None
    children: Optional[List["TreeNode"]] = None


class TreeListEntry(BaseModel):
    name: str
    path: str
    type: Literal["file", "directory"]
    size: Optional[int] = None
    mtime: Optional[float] = None


class FnlUploadResult(BaseModel):
    filename: str
    staging_path: str
    size_bytes: int
    message: str


class FnlVerifyResult(BaseModel):
    filename: str
    valid: bool
    size_bytes: int
    checks: dict[str, Any]
    message: str


class FnlCompleteResult(BaseModel):
    filename: str
    archive_path: str
    message: str


class RepairRequest(BaseModel):
    filename: str
    date: str
    hour: str
    requested_at: str
    region: str
    status: Literal["pending", "uploaded", "verified", "completed", "expired"]


class FnlScanResult(BaseModel):
    start_date: str
    end_date: str
    missing: list[str]
    total: int
    available: int


class RunSummary(BaseModel):
    run_id: str
    region: str
    season: str
    pre: str
    start_date: str
    variant: str = ""
    run_root: str
    state: Optional[Dict[str, Any]] = None
    effective_state: Optional[Dict[str, Any]] = None
    anomalies: List[str] = Field(default_factory=list)
    slurm_jobs: List[Dict[str, str]] = Field(default_factory=list)
    progress: Optional[float] = None


class DaemonStatus(BaseModel):
    started_at: str
    schedule_enabled: bool
    tianqing_enabled: bool = False
    last_tick_at: Optional[str] = None
    last_tick_result: Optional[str] = None
    next_tick_at: Optional[str] = None
    tianqing_done_date: Optional[str] = None
    tianqing_last_attempt_at: Optional[str] = None
    tianqing_last_result: Optional[str] = None
    tianqing_next_attempt_at: Optional[str] = None
    last_reconcile_at: Optional[str] = None
    active_runs: int = 0
    pending_repairs: int = 0
    server_time_utc: str
    server_time_local: str


class TickResult(BaseModel):
    date: str
    season: Optional[str] = None
    triggered_at: str
    regions_submitted: list[str]
    regions_skipped: list[str]
    fnl_gfs_used: int
    repair_requests_created: int
    messages: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    uptime_seconds: float
    schedule_enabled: bool


class RegionInfo(BaseModel):
    region: str
    display_name: str
    seasons: list[str]
    slurm_code: str


class LogTailResponse(BaseModel):
    path: str
    lines: list[str]
    truncated: bool
