"""天擎日均气温数据定时下载。"""

from __future__ import annotations

import csv
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from file_tree import ensure_state_dir
from models import AppConfig
from run_manager import _save_daemon_state, get_daemon_state

logger = logging.getLogger("smanager.tianqing")

DEFAULT_SCRIPT = (
    "/g7/anxq/Zhangjt/workspace/auto-pollen-lijt/"
    "Tianqing_data_download/music-sdk-scriptFile-v2.0/download_dates.sh"
)
DEFAULT_DATA_DIR = (
    "/g7/anxq/Zhangjt/workspace/pollen_emission/Mete_Data/Tianqing_TEM_Avg_download"
)
MISSING_TEM_VALUE = 999999


def _tianqing_tz(config: AppConfig) -> ZoneInfo:
    tz_name = config.tianqing.timezone or config.schedule.timezone
    return ZoneInfo(tz_name)


def _count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def _has_valid_tem_avg(path: Path) -> bool:
    """CSV 中是否至少有一条有效 TEM_Avg（非 999999 且 <= 50）。"""
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                raw = row.get("TEM_Avg")
                if raw is None:
                    continue
                try:
                    value = float(raw)
                except ValueError:
                    continue
                if value != MISSING_TEM_VALUE and value <= 50:
                    return True
    except OSError:
        return False
    return False


def _purge_invalid_tianqing_csv(path: Path) -> bool:
    """若文件全部为缺测值则删除，返回是否已删除。"""
    if not path.is_file():
        return False
    if _has_valid_tem_avg(path):
        return False
    try:
        path.unlink()
    except OSError as exc:
        logger.warning("删除无效天擎 CSV 失败: %s (%s)", path, exc)
        return False
    logger.info("天擎数据全为缺测(999999)，已删除: %s", path)
    return True


def tianqing_data_exists(config: AppConfig, date_str: str) -> bool:
    csv_path = Path(config.tianqing.data_dir) / f"{date_str}.csv"
    if not csv_path.is_file():
        return False
    if _count_lines(csv_path) <= config.tianqing.min_lines:
        _purge_invalid_tianqing_csv(csv_path)
        return False
    if not _has_valid_tem_avg(csv_path):
        _purge_invalid_tianqing_csv(csv_path)
        return False
    return True


def _parse_hhmm(value: str) -> tuple[int, int]:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(f"无效时间格式: {value}")
    return int(parts[0]), int(parts[1])


def next_tianqing_attempt_at(config: AppConfig) -> Optional[str]:
    if not config.tianqing.enabled:
        return None

    tz = _tianqing_tz(config)
    now = datetime.now(tz)
    today = now.strftime("%Y%m%d")

    if tianqing_data_exists(config, today):
        return None

    state = get_daemon_state()
    if state.get("tianqing_done_date") == today:
        return None

    start_hour, start_minute = _parse_hhmm(config.tianqing.start_time)
    start_moment = now.replace(
        hour=start_hour,
        minute=start_minute,
        second=0,
        microsecond=0,
    )
    if now < start_moment:
        return start_moment.isoformat()

    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return next_hour.isoformat()


def run_tianqing_download(config: AppConfig, date_str: str) -> dict:
    script = Path(config.tianqing.script_path)
    if not script.is_file():
        message = f"天擎下载脚本不存在: {script}"
        logger.error(message)
        return {"ok": False, "message": message}

    log_dir = ensure_state_dir() / "tianqing_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"{date_str}_{stamp}.log"

    logger.info("开始天擎下载: date=%s script=%s", date_str, script)
    try:
        proc = subprocess.run(
            ["bash", str(script), date_str, date_str],
            capture_output=True,
            text=True,
            timeout=config.tianqing.timeout_seconds,
            cwd=str(script.parent),
            check=False,
        )
    except subprocess.TimeoutExpired:
        message = f"天擎下载超时 ({config.tianqing.timeout_seconds}s): {date_str}"
        logger.error(message)
        log_path.write_text(message + "\n", encoding="utf-8")
        return {"ok": False, "message": message, "log_path": str(log_path)}

    output = (proc.stdout or "") + (proc.stderr or "")
    log_path.write_text(output, encoding="utf-8")

    csv_path = Path(config.tianqing.data_dir) / f"{date_str}.csv"
    purged_invalid = False
    if csv_path.is_file() and not _has_valid_tem_avg(csv_path):
        purged_invalid = _purge_invalid_tianqing_csv(csv_path)

    exists = tianqing_data_exists(config, date_str)
    ok = proc.returncode == 0 and exists
    if ok:
        message = f"天擎数据已就绪: {date_str}"
    elif exists:
        message = f"天擎数据已存在（脚本退出码 {proc.returncode}）: {date_str}"
        ok = True
    elif purged_invalid:
        message = (
            f"天擎下载完成但观测尚未发布（全为 {MISSING_TEM_VALUE}），"
            f"已删除无效文件: {date_str}；将在下一小时继续重试"
        )
    else:
        message = f"天擎下载失败: {date_str} (exit={proc.returncode})"

    logger.info("%s log=%s", message, log_path)
    return {
        "ok": ok,
        "message": message,
        "exit_code": proc.returncode,
        "log_path": str(log_path),
    }


def maybe_run_tianqing_download(config: AppConfig) -> None:
    """北京时间 start_time 起每小时尝试下载当天数据，直到有效数据就绪。

    若下载结果全为缺测(999999)，会删除无效文件并在下一小时继续重试，
    不会标记 tianqing_done_date。
    """
    if not config.tianqing.enabled:
        return

    tz = _tianqing_tz(config)
    now = datetime.now(tz)
    today = now.strftime("%Y%m%d")
    state = get_daemon_state()

    if state.get("tianqing_done_date") and state.get("tianqing_done_date") != today:
        _save_daemon_state(
            {
                "tianqing_done_date": None,
                "tianqing_last_slot": None,
                "tianqing_last_result": None,
            }
        )
        state = get_daemon_state()

    if tianqing_data_exists(config, today):
        if state.get("tianqing_done_date") != today:
            _save_daemon_state(
                {
                    "tianqing_done_date": today,
                    "tianqing_last_result": "exists",
                    "tianqing_last_attempt_at": now.isoformat(),
                }
            )
            logger.info("天擎数据已存在，跳过下载: %s", today)
        return

    start_hour, start_minute = _parse_hhmm(config.tianqing.start_time)
    start_moment = now.replace(
        hour=start_hour,
        minute=start_minute,
        second=0,
        microsecond=0,
    )
    if now < start_moment:
        return

    slot = f"{today}T{now.hour:02d}"
    if state.get("tianqing_last_slot") == slot:
        return

    result = run_tianqing_download(config, today)
    exists = tianqing_data_exists(config, today)
    message = result.get("message") or ""
    if exists:
        last_result = "success"
    elif "尚未发布" in message:
        last_result = "pending"
    else:
        last_result = "failed"
    patch = {
        "tianqing_last_slot": slot,
        "tianqing_last_attempt_at": now.isoformat(),
        "tianqing_last_result": last_result,
        "tianqing_last_message": message,
        "tianqing_next_attempt_at": next_tianqing_attempt_at(config),
    }
    if exists:
        patch["tianqing_done_date"] = today
    elif last_result == "pending":
        logger.info("天擎观测尚未发布，下一小时重试: %s", today)
    _save_daemon_state(patch)
