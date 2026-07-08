"""配置加载与持久化。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from models import AppConfig, ConfigUpdate, FileTreeRoot, FileTreeRootsConfig, PathsConfig

SERVER_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = SERVER_DIR / "config.yaml"
EXAMPLE_CONFIG_PATH = SERVER_DIR / "config.example.yaml"


def _default_paths() -> PathsConfig:
    return PathsConfig(
        project_root="/g7/anxq/Zhangjt/workspace/auto-pollen-lijt",
        fnl_staging="/g7/anxq/Zhangjt/static/fnl/staging",
        fnl_archive="/g7/anxq/Zhangjt/static/fnl",
        wgrib2="/g1/app/mathlib/wgrib2/2.0.6/intel/bin/wgrib2",
        fnl_min_mb=5.0,
    )


def _default_file_tree() -> FileTreeRootsConfig:
    return FileTreeRootsConfig(
        roots={
            "project": FileTreeRoot(path=".", label="项目根目录"),
            "runs": FileTreeRoot(path="runs", label="运行目录"),
            "output": FileTreeRoot(path="output", label="输出目录"),
            "logs": FileTreeRoot(path="logs", label="日志目录"),
            "fnl": FileTreeRoot(
                path="/g7/anxq/Zhangjt/static/fnl",
                label="FNL 补给目录",
            ),
        }
    )


def ensure_config_file() -> Path:
    if not DEFAULT_CONFIG_PATH.exists():
        if EXAMPLE_CONFIG_PATH.exists():
            shutil.copy(EXAMPLE_CONFIG_PATH, DEFAULT_CONFIG_PATH)
        else:
            cfg = AppConfig(paths=_default_paths(), file_tree=_default_file_tree())
            save_config(cfg)
    return DEFAULT_CONFIG_PATH


def load_config() -> AppConfig:
    ensure_config_file()
    with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    if "paths" not in raw:
        raw["paths"] = _default_paths().model_dump()
    if "file_tree" not in raw:
        raw["file_tree"] = _default_file_tree().model_dump()

    return AppConfig.model_validate(raw)


def save_config(config: AppConfig) -> None:
    data = config.model_dump(mode="json")
    tmp = DEFAULT_CONFIG_PATH.with_suffix(".yaml.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)
    tmp.replace(DEFAULT_CONFIG_PATH)


def apply_config_update(config: AppConfig, update: ConfigUpdate) -> AppConfig:
    if update.schedule_enabled is not None:
        config.schedule.enabled = update.schedule_enabled
    if update.tianqing_enabled is not None:
        config.tianqing.enabled = update.tianqing_enabled
    if update.tick_time is not None:
        config.schedule.tick_time = update.tick_time
    if update.repair_deadline is not None:
        config.schedule.repair_deadline = update.repair_deadline
    if update.regions is not None:
        config.forecast.regions = update.regions
    if update.season is not None:
        config.forecast.season = update.season
    if update.pre is not None:
        config.forecast.pre = update.pre
    if update.fnl_gfs_default is not None:
        config.forecast.fnl_gfs_default = update.fnl_gfs_default
    if update.fnl_gfs_fallback is not None:
        config.forecast.fnl_gfs_fallback = update.fnl_gfs_fallback
    if update.innermg_autumn_variant is not None:
        config.forecast.innermg_autumn_variant = update.innermg_autumn_variant
    return config
