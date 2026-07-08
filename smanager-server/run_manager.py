"""Run 扫描、提交与状态恢复。"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from file_tree import ensure_state_dir
from models import AppConfig, FnlScanResult, RunSummary, TickResult

RUN_NAME_RE = re.compile(r"^(\d{8})(pre\d+)(?:_(caoditu))?(?:_(\d+))?$")
FNL_RELEASE_LAG_HOURS = 8  # FNL 通常滞后约 6-8 小时发布


def _project_root(config: AppConfig) -> Path:
    return Path(config.paths.project_root)


def _append_event(message: str, level: str = "info", extra: Optional[Dict] = None) -> None:
    state_dir = ensure_state_dir()
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
    }
    if extra:
        event.update(extra)
    with (state_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _save_daemon_state(patch: dict) -> None:
    state_dir = ensure_state_dir()
    path = state_dir / "daemon_state.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data.update(patch)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_daemon_state() -> dict:
    path = ensure_state_dir() / "daemon_state.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def resolve_season_from_month(month: int) -> Optional[str]:
    """按月份决定预报季节：3-6 春季，7-10 秋季，其余不预报。"""
    if 3 <= month <= 6:
        return "spring"
    if 7 <= month <= 10:
        return "autumn"
    return None


def resolve_season_for_date(date_str: str) -> Optional[str]:
    return resolve_season_from_month(int(date_str[4:6]))


def regions_for_season(config: AppConfig, season: str) -> List[str]:
    root = _project_root(config)
    sys.path.insert(0, str(root))
    from config.registry import REGIONS  # noqa: WPS433

    valid: List[str] = []
    for region in config.forecast.regions:
        key = region if region in REGIONS else region.replace("_", "")
        profile = REGIONS.get(key)
        if profile and season in profile.templates:
            valid.append(region)
    return valid


def beijing_today(config: AppConfig) -> str:
    tz = ZoneInfo(config.schedule.timezone)
    return datetime.now(tz).strftime("%Y%m%d")


def _fnl_nominal_utc(filename: str) -> datetime:
    date_str = filename[4:12]
    hour = int(filename[13:15])
    return datetime.strptime(date_str, "%Y%m%d").replace(
        hour=hour, minute=0, second=0, tzinfo=timezone.utc
    )


def split_repairable_fnl(
    filenames: List[str],
    now_utc: Optional[datetime] = None,
) -> Tuple[List[str], List[str]]:
    """区分可修补（已应发布）与尚未到发布时间的 FNL 时次。"""
    now_utc = now_utc or datetime.now(timezone.utc)
    repairable: List[str] = []
    not_released: List[str] = []
    for fname in filenames:
        nominal = _fnl_nominal_utc(fname)
        if nominal + timedelta(hours=FNL_RELEASE_LAG_HOURS) <= now_utc:
            repairable.append(fname)
        else:
            not_released.append(fname)
    return repairable, not_released


def scan_fnl_for_date(
    config: AppConfig,
    start_date: str,
    season: str,
) -> FnlScanResult:
    root = _project_root(config)
    sys.path.insert(0, str(root))
    from config.registry import get_pre_mode  # noqa: WPS433
    from scripts.copy_fnl import scan_wps_window_detail  # noqa: WPS433
    from scripts.dates import ForecastWindow  # noqa: WPS433

    pre = config.forecast.pre
    region = config.forecast.regions[0] if config.forecast.regions else "Beijing"
    mode = get_pre_mode(region, pre, season)
    window = ForecastWindow(start_date, mode.predict_days, config.forecast.fnl_gfs_default)
    fnl_wps_start, fnl_wps_end = window.fnl_wps_range()
    missing, damaged, total, _ = scan_wps_window_detail(fnl_wps_start, fnl_wps_end)
    fnl_start, fnl_end = window.fnl_copy_range()
    return FnlScanResult(
        start_date=fnl_start,
        end_date=fnl_end,
        missing=missing + damaged,
        total=total,
        available=total - len(missing) - len(damaged),
    )


def _innermg_autumn_variants(config: AppConfig, season: str) -> List[str]:
    """返回 InnerMG 秋季需提交的 variant 列表（''=标准，'caoditu'=草地TIF）。"""
    if season != "autumn":
        return [""]
    mode = config.forecast.innermg_autumn_variant
    if mode == "both":
        return ["", "caoditu"]
    if mode == "caoditu":
        return ["caoditu"]
    return [""]


def _region_tick_label(region: str, variant: str) -> str:
    if variant == "caoditu":
        return f"{region}(caoditu)"
    return region


def _run_exists(
    config: AppConfig,
    region: str,
    start_date: str,
    season: str,
    variant: str = "",
) -> bool:
    root = _project_root(config)
    sys.path.insert(0, str(root))
    from config.layout import predict_run_name, predict_variant_suffix  # noqa: WPS433

    season_key = season.lower()
    region_key = region.lower()
    pre = config.forecast.pre
    base = root / "runs" / "predict" / season_key / region_key
    if not base.is_dir():
        return False

    suffix = predict_variant_suffix(variant)
    target = predict_run_name(pre, start_date, suffix)
    pattern = re.compile(rf"^{re.escape(target)}(?:_\d+)?$")
    return any(p.is_dir() and pattern.match(p.name) for p in base.iterdir())


def _submit_region(
    config: AppConfig,
    region: str,
    start_date: str,
    season: str,
    fnl_gfs: int,
    variant: str = "",
) -> tuple[bool, str]:
    root = _project_root(config)
    pre = config.forecast.pre

    env = os.environ.copy()
    env["TASK_DUP_ACTION"] = config.forecast.task_dup_action
    cmd = [
        "bash",
        "scripts/batch_forecast.sh",
        "--region",
        region,
        "--season",
        season,
        "--pre",
        pre,
        "--start",
        start_date,
        "--fnl-gfs",
        str(fnl_gfs),
    ]
    if variant:
        cmd.extend(["--variant", variant])

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "提交超时"
    except OSError as exc:
        return False, str(exc)

    ok = proc.returncode == 0
    combined = "\n".join(filter(None, [proc.stdout, proc.stderr])).strip()
    msg = combined[-1000:]
    return ok, msg


def run_tick(
    config: AppConfig,
    force: bool = False,
    start_date: Optional[str] = None,
    season: Optional[str] = None,
) -> TickResult:
    from repair_requests import create_repair_request

    tz = ZoneInfo(config.schedule.timezone)
    now = datetime.now(tz)
    date = start_date or now.strftime("%Y%m%d")
    messages: list[str] = []
    submitted: list[str] = []
    skipped: list[str] = []

    effective_season = season or resolve_season_for_date(date)
    if effective_season is None:
        month = int(date[4:6])
        messages.append(f"{month} 月不在预报窗口（春季 3-6 月，秋季 7-10 月），跳过")
        result = TickResult(
            date=date,
            season=None,
            triggered_at=now.isoformat(),
            regions_submitted=[],
            regions_skipped=[],
            fnl_gfs_used=0,
            repair_requests_created=0,
            messages=messages,
        )
        _save_daemon_state(
            {
                "last_tick_at": now.isoformat(),
                "last_tick_result": "off_season",
                "last_tick_detail": result.model_dump(),
            }
        )
        _append_event("tick 非预报月份", extra={"date": date, "month": month})
        return result

    regions = regions_for_season(config, effective_season)
    if not regions:
        messages.append(f"季节 {effective_season} 下无可用区域（请检查 forecast.regions 配置）")
        result = TickResult(
            date=date,
            season=effective_season,
            triggered_at=now.isoformat(),
            regions_submitted=[],
            regions_skipped=[],
            fnl_gfs_used=0,
            repair_requests_created=0,
            messages=messages,
        )
        _save_daemon_state(
            {
                "last_tick_at": now.isoformat(),
                "last_tick_result": "no_regions",
                "last_tick_detail": result.model_dump(),
            }
        )
        return result

    messages.append(f"预报季节: {effective_season}，区域: {', '.join(regions)}")

    today_bj = now.strftime("%Y%m%d")
    if date > today_bj and not force:
        messages.append(f"预报日 {date} 晚于今天 {today_bj}，跳过（勿对未来日期自动 tick）")
        result = TickResult(
            date=date,
            season=effective_season,
            triggered_at=now.isoformat(),
            regions_submitted=[],
            regions_skipped=regions,
            fnl_gfs_used=0,
            repair_requests_created=0,
            messages=messages,
        )
        _save_daemon_state(
            {
                "last_tick_at": now.isoformat(),
                "last_tick_result": "future_date",
                "last_tick_detail": result.model_dump(),
            }
        )
        _append_event("tick 未来预报日", extra={"date": date, "today": today_bj})
        return result

    fnl_scan = scan_fnl_for_date(config, date, effective_season)
    repairable_missing, not_released = split_repairable_fnl(fnl_scan.missing)
    repair_created = 0
    if repairable_missing:
        for fname in repairable_missing:
            create_repair_request(config, fname, regions[0], config.schedule.timezone)
            repair_created += 1
        messages.append(
            f"FNL 缺失 {len(repairable_missing)}/{fnl_scan.total}，已创建 repair request"
        )
    if not_released:
        messages.append(
            f"跳过 {len(not_released)} 个尚未发布的 FNL 时次"
            f"（例: {not_released[0]}）"
        )

    fnl_gfs = config.forecast.fnl_gfs_default
    deadline_parts = config.schedule.repair_deadline.split(":")
    if len(deadline_parts) == 2:
        dl_h, dl_m = int(deadline_parts[0]), int(deadline_parts[1])
        deadline = now.replace(hour=dl_h, minute=dl_m, second=0, microsecond=0)
        if repairable_missing and now >= deadline:
            fnl_gfs = min(config.forecast.fnl_gfs_default + 1, 3)
            messages.append(
                f"已过 repair deadline，降级 fnl_gfs"
                f" {config.forecast.fnl_gfs_default} → {fnl_gfs}（GFS 向前补时次）"
            )
        elif repairable_missing and now < deadline:
            messages.append("等待 FNL repair，暂不提交（可手动 force 或等到 deadline）")
            if not force:
                result = TickResult(
                    date=date,
                    season=effective_season,
                    triggered_at=now.isoformat(),
                    regions_submitted=[],
                    regions_skipped=regions,
                    fnl_gfs_used=fnl_gfs,
                    repair_requests_created=repair_created,
                    messages=messages,
                )
                _save_daemon_state({"last_tick_at": now.isoformat(), "last_tick_result": "waiting_fnl"})
                _append_event("tick 等待 FNL", extra={"date": date, "missing": len(repairable_missing)})
                return result

    for region in regions:
        variants = (
            _innermg_autumn_variants(config, effective_season)
            if region == "InnerMG"
            else [""]
        )
        for variant in variants:
            label = _region_tick_label(region, variant)
            if not force and _run_exists(
                config, region, date, effective_season, variant=variant
            ):
                skipped.append(label)
                messages.append(f"{label} 已有 {date} 运行目录，跳过")
                continue
            ok, msg = _submit_region(
                config, region, date, effective_season, fnl_gfs, variant=variant
            )
            if ok:
                submitted.append(label)
                messages.append(f"{label} 提交成功")
            else:
                skipped.append(label)
                messages.append(f"{label} 提交失败: {msg}")
                _append_event(f"{label} 提交失败", level="error", extra={"msg": msg})

    result = TickResult(
        date=date,
        season=effective_season,
        triggered_at=now.isoformat(),
        regions_submitted=submitted,
        regions_skipped=skipped,
        fnl_gfs_used=fnl_gfs,
        repair_requests_created=repair_created,
        messages=messages,
    )
    _save_daemon_state(
        {
            "last_tick_at": now.isoformat(),
            "last_tick_result": "ok" if submitted else "skipped",
            "last_tick_detail": result.model_dump(),
        }
    )
    _append_event("tick 完成", extra=result.model_dump())
    return result


def reconcile(config: AppConfig) -> dict:
    runs = list_runs(config, limit=50)
    slurm = query_slurm_jobs()
    anomaly_runs = [item for item in runs if item.anomalies]
    now = datetime.now(timezone.utc).isoformat()
    _save_daemon_state({"last_reconcile_at": now, "active_slurm_jobs": len(slurm)})
    _append_event(
        "reconcile 完成",
        extra={"runs": len(runs), "slurm_jobs": len(slurm), "anomaly_runs": len(anomaly_runs)},
    )
    return {
        "reconciled_at": now,
        "runs_found": len(runs),
        "slurm_jobs": slurm,
        "anomaly_runs": [
            {
                "run_id": item.run_id,
                "region": item.region,
                "season": item.season,
                "anomalies": item.anomalies,
            }
            for item in anomaly_runs[:20]
        ],
    }


def query_slurm_jobs() -> list[dict[str, str]]:
    try:
        proc = subprocess.run(
            ["squeue", "-u", os.environ.get("USER", ""), "-h", "-o", "%i %j %T %M"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    if proc.returncode != 0:
        return []
    jobs = []
    for line in proc.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 3:
            jobs.append(
                {
                    "job_id": parts[0],
                    "name": parts[1],
                    "state": parts[2],
                    "time": parts[3] if len(parts) > 3 else "",
                }
            )
    return jobs


def _parse_run_dir(path: Path) -> Optional[Tuple[str, str, str, str]]:
    m = RUN_NAME_RE.match(path.name)
    if not m:
        return None
    start_date, pre = m.group(1), m.group(2)
    variant = m.group(3) or ""
    return start_date, pre, path.name, variant


def _read_state_json(run_dir: Path) -> Optional[Dict]:
    state_file = run_dir / "state.json"
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _estimate_progress(run_dir: Path) -> Optional[float]:
    wrf_dir = run_dir / "wrf"
    if not wrf_dir.is_dir():
        return None
    wrfouts = sorted(wrf_dir.glob("wrfout_d01_*"))
    if len(wrfouts) < 2:
        return None
    try:
        first = wrfouts[0].name.split("_")[-1]
        last = wrfouts[-1].name.split("_")[-1]
        t0 = datetime.strptime(first, "%Y-%m-%d_%H:%M:%S")
        t1 = datetime.strptime(last, "%Y-%m-%d_%H:%M:%S")
        if t1 <= t0:
            return None
        return min(1.0, max(0.0, (t1 - t0).total_seconds() / (9 * 24 * 3600)))
    except ValueError:
        return None


SLURM_ACTIVE_STATES = {"RUNNING", "PENDING", "CONFIGURING", "COMPLETING", "SUSPENDED"}
SLURM_FAILED_STATES = {"FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL", "PREEMPTED", "DEADLINE"}
DONE_STATE_VALUES = {"done", "success", "completed", "skipped"}
RUNNING_STATE_VALUES = {"running", "active"}
PIPELINE_STAGES = (
    "geogrid",
    "linkgrib",
    "ungrib",
    "metgrid",
    "real",
    "wrfchemi",
    "wrf",
    "postprocess",
)
STAGE_JOB_PREFIXES: dict[str, tuple[str, ...]] = {
    "geogrid": ("geogrid_", "prep_"),
    "linkgrib": ("prep_",),
    "ungrib": ("prep_",),
    "metgrid": ("prep_",),
    "real": ("real_", "prep_"),
    "wrfchemi": ("wrfchemi_", "chemi_", "prep_"),
    "wrf": ("wrf_",),
    "postprocess": ("post_", "postprocess_"),
    # 旧版 state 兼容
    "wps": ("wps_", "geogrid_", "prep_"),
}


def query_sacct_jobs(days_back: int = 3) -> list[dict[str, str]]:
    user = os.environ.get("USER", "")
    if not user:
        return []
    try:
        proc = subprocess.run(
            [
                "sacct",
                "-n",
                "-u",
                user,
                f"--starttime=now-{days_back}days",
                "-o",
                "JobID,JobName,State,ExitCode",
                "-P",
                "--noheader",
            ],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    if proc.returncode != 0:
        return []
    jobs: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) < 4:
            continue
        job_id, name, state, exit_code = parts[0], parts[1], parts[2], parts[3]
        if "." in job_id:
            continue
        jobs.append(
            {
                "job_id": job_id,
                "name": name,
                "state": state,
                "exit_code": exit_code,
            }
        )
    return jobs


def _read_tail_text(path: Path, max_bytes: int = 4096) -> str:
    if not path.is_file():
        return ""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if len(data) > max_bytes:
        data = data[-max_bytes:]
    return data.decode("utf-8", errors="replace")


def _failure_hints(run_dir: Path) -> list[str]:
    hints: list[str] = []
    checks = [
        ("wrf/rsl.error.0000", ("error", "fail", "fatal", "abort")),
        ("wrf/wrf.log", ("error", "fail", "fatal")),
        ("real/real.log", ("error", "fail", "fatal")),
        ("prep.log", ("error", "fail", "fatal")),
    ]
    for rel, keywords in checks:
        text = _read_tail_text(run_dir / rel)
        if not text.strip():
            continue
        lower = text.lower()
        if any(keyword in lower for keyword in keywords):
            hints.append(f"{rel} 含错误关键字")
        elif rel.endswith("rsl.error.0000") and len(text.strip()) > 80:
            hints.append(f"{rel} 非空（WRF 可能异常退出）")
    return hints


def _job_matches_stage(job_name: str, stage: str, tag: str) -> bool:
    if tag not in job_name:
        return False
    prefixes = STAGE_JOB_PREFIXES.get(stage, ())
    return any(job_name.startswith(prefix) for prefix in prefixes)


def _active_slurm_for_tag(slurm_jobs: list[dict[str, str]], tag: str) -> list[dict[str, str]]:
    return [
        job
        for job in slurm_jobs
        if tag in job.get("name", "") and (job.get("state") or "").upper() in SLURM_ACTIVE_STATES
    ]


def _failed_sacct_for_tag(sacct_jobs: list[dict[str, str]], tag: str) -> list[dict[str, str]]:
    return [
        job
        for job in sacct_jobs
        if tag in job.get("name", "") and (job.get("state") or "").upper() in SLURM_FAILED_STATES
    ]


def _stage_status_from_state(state: Optional[Dict[str, Any]], stage: str) -> str:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from scripts.run_state import stage_status  # noqa: WPS433

    return stage_status(state, stage)


def diagnose_run(
    run_dir: Path,
    *,
    state: Optional[Dict[str, Any]],
    slurm_jobs: list[dict[str, str]],
    tag: str,
    sacct_jobs: Optional[list[dict[str, str]]] = None,
) -> tuple[dict[str, Any], list[str]]:
    """结合 state.json、squeue、sacct 与日志推断有效阶段状态。"""
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from scripts.run_state import flatten_effective_state  # noqa: WPS433

    raw_state = dict(state or {})
    effective = flatten_effective_state(raw_state)
    anomalies: list[str] = []

    sacct = sacct_jobs if sacct_jobs is not None else query_sacct_jobs()
    active = _active_slurm_for_tag(slurm_jobs, tag)
    failed_sacct = _failed_sacct_for_tag(sacct, tag)
    log_hints = _failure_hints(run_dir)

    running_stages = [
        stage
        for stage in PIPELINE_STAGES
        if _stage_status_from_state(raw_state, stage) in RUNNING_STATE_VALUES
    ]
    if running_stages and not active:
        anomalies.append(f"state.json 标记 {running_stages} 为运行中，但 squeue 无匹配活跃任务")
        for stage in running_stages:
            stage_failed = [
                job
                for job in failed_sacct
                if _job_matches_stage(job.get("name", ""), stage, tag)
            ]
            if stage_failed:
                job = stage_failed[0]
                effective[stage] = "failed"
                anomalies.append(
                    f"sacct: {job.get('name')} 已 {job.get('state')} (exit={job.get('exit_code')})"
                )
            elif log_hints:
                effective[stage] = "failed"
                anomalies.extend(log_hints[:2])
            else:
                anomalies.append("建议查看 wrf/rsl.error.0000 或 sacct 输出")

    last_done_idx = -1
    for idx, stage in enumerate(PIPELINE_STAGES):
        if _stage_status_from_state(raw_state, stage) in DONE_STATE_VALUES:
            last_done_idx = idx

    if last_done_idx >= 0 and not active:
        next_stage = PIPELINE_STAGES[last_done_idx + 1] if last_done_idx + 1 < len(PIPELINE_STAGES) else None
        if next_stage:
            next_raw = _stage_status_from_state(raw_state, next_stage)
            if next_raw in {"", "pending"}:
                stage_failed = [
                    job
                    for job in failed_sacct
                    if _job_matches_stage(job.get("name", ""), next_stage, tag)
                ]
                if stage_failed:
                    job = stage_failed[0]
                    effective[next_stage] = "failed"
                    anomalies.append(
                        f"阶段 {next_stage} 未写入 state，但 sacct 显示 {job.get('name')} {job.get('state')}"
                    )
                elif next_stage == "wrf" and log_hints:
                    effective["wrf"] = "failed"
                    anomalies.extend(log_hints[:2])

    if failed_sacct and not any(str(v).lower() in {"failed", "fail", "error"} for v in effective.values()):
        job = failed_sacct[0]
        anomalies.append(
            f"近期 Slurm 任务失败: {job.get('name')} ({job.get('state')}, exit={job.get('exit_code')})"
        )

    return effective, anomalies


def _build_run_summary(
    run_dir: Path,
    *,
    region: str,
    season: str,
    run_id: str,
    start_date: str,
    pre: str,
    variant: str = "",
    slurm_jobs: list[dict[str, str]],
    sacct_jobs: Optional[list[dict[str, str]]] = None,
) -> RunSummary:
    tag = f"{region.lower()}_{season.lower()}_{run_id}"
    matched_jobs = [job for job in slurm_jobs if tag in job.get("name", "")]
    state = _read_state_json(run_dir)
    effective, anomalies = diagnose_run(
        run_dir,
        state=state,
        slurm_jobs=matched_jobs,
        tag=tag,
        sacct_jobs=sacct_jobs,
    )
    return RunSummary(
        run_id=run_id,
        region=region.lower(),
        season=season.lower(),
        pre=pre,
        start_date=start_date,
        variant=variant,
        run_root=str(run_dir),
        state=state,
        effective_state=effective,
        anomalies=anomalies,
        slurm_jobs=matched_jobs,
        progress=_estimate_progress(run_dir),
    )


def list_runs(config: AppConfig, limit: int = 30) -> list[RunSummary]:
    root = _project_root(config)
    predict_root = root / "runs" / "predict"
    if not predict_root.is_dir():
        return []

    slurm_jobs = query_slurm_jobs()
    sacct_jobs = query_sacct_jobs()
    summaries: list[RunSummary] = []

    for season_dir in sorted(predict_root.iterdir(), reverse=True):
        if not season_dir.is_dir():
            continue
        for region_dir in sorted(season_dir.iterdir(), reverse=True):
            if not region_dir.is_dir():
                continue
            for run_dir in sorted(region_dir.iterdir(), reverse=True):
                if not run_dir.is_dir():
                    continue
                parsed = _parse_run_dir(run_dir)
                if not parsed:
                    continue
                start_date, pre, run_id, variant = parsed
                summaries.append(
                    _build_run_summary(
                        run_dir,
                        region=region_dir.name,
                        season=season_dir.name,
                        run_id=run_id,
                        start_date=start_date,
                        pre=pre,
                        variant=variant,
                        slurm_jobs=slurm_jobs,
                        sacct_jobs=sacct_jobs,
                    )
                )
                if len(summaries) >= limit:
                    return summaries
    return summaries


def get_run_detail(config: AppConfig, season: str, region: str, run_id: str) -> RunSummary:
    from fastapi import HTTPException

    root = _project_root(config)
    run_dir = root / "runs" / "predict" / season.lower() / region.lower() / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="run 不存在")
    parsed = _parse_run_dir(run_dir)
    if not parsed:
        raise HTTPException(status_code=400, detail="无法解析 run 目录名")
    start_date, pre, _, variant = parsed
    slurm_jobs = query_slurm_jobs()
    return _build_run_summary(
        run_dir,
        region=region,
        season=season,
        run_id=run_id,
        start_date=start_date,
        pre=pre,
        variant=variant,
        slurm_jobs=slurm_jobs,
    )
