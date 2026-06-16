#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator


def date_range(start: datetime, end: datetime):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def target_grid(args):
    lat = np.linspace(args.lat_min, args.lat_max, int((args.lat_max - args.lat_min) / args.resolution + 1))
    lon = np.linspace(args.lon_min, args.lon_max, int((args.lon_max - args.lon_min) / args.resolution + 1))
    xlon, xlat = np.meshgrid(lon, lat)
    return lat, lon, xlat, xlon


def run_wgrib2_to_nc(wgrib2: str, grib: Path, out_nc: Path) -> None:
    cmd = [
        wgrib2,
        str(grib),
        "-match",
        ":TMP:2 m above ground:",
        "-netcdf",
        str(out_nc),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0 or not out_nc.exists():
        raise RuntimeError(f"wgrib2 failed for {grib}: {result.stdout[-1000:]}")


def extract_t2_c(wgrib2: str, grib: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with tempfile.TemporaryDirectory(prefix="t2_") as tmp:
        out_nc = Path(tmp) / "t2.nc"
        run_wgrib2_to_nc(wgrib2, grib, out_nc)
        ds = nc.Dataset(out_nc)
        try:
            lat = np.array(ds.variables["latitude"][:], dtype=float)
            lon = np.array(ds.variables["longitude"][:], dtype=float)
            data = np.array(ds.variables["TMP_2maboveground"][0, :, :], dtype=float) - 273.15
        finally:
            ds.close()
    return lat, lon, data


def interpolate_to_target(args, lat: np.ndarray, lon: np.ndarray, data: np.ndarray) -> pd.DataFrame:
    tlat, tlon, xlat, xlon = target_grid(args)
    if lat[0] > lat[-1]:
        lat = lat[::-1]
        data = data[::-1, :]
    interpolator = RegularGridInterpolator((lat, lon), data, bounds_error=False, fill_value=np.nan)
    values = interpolator(np.array([xlat.flatten(), xlon.flatten()]).T).reshape(xlat.shape)
    return pd.DataFrame(values, index=tlat, columns=tlon)


def write_daily_mean(frames: list[pd.DataFrame], out_dir: Path) -> pd.DataFrame:
    if not frames:
        raise RuntimeError(f"no temperature frames for {out_dir}")
    mean = sum(frames) / float(len(frames))
    out_dir.mkdir(parents=True, exist_ok=True)
    mean.to_csv(out_dir / "TEM_Avg.csv", float_format="%.2f", na_rep="NaN")
    return mean


def read_daily_mean(out_dir: Path) -> pd.DataFrame | None:
    path = out_dir / "TEM_Avg.csv"
    if not path.exists():
        return None
    frame = pd.read_csv(path, index_col=0)
    frame.index = frame.index.astype(float)
    frame.columns = frame.columns.astype(float)
    return frame


def append_missing_report(out_root: Path, records: list[str]) -> None:
    if not records:
        return
    out_root.mkdir(parents=True, exist_ok=True)
    with (out_root / "missing_temperature_inputs.log").open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(record)
            handle.write("\n")


def fnl_path(root: Path, when: datetime) -> Path:
    name = f"fnl_{when:%Y%m%d}_{when:%H}_00.grib2"
    candidates = [
        root / f"{when:%Y}" / f"{when:%Y%m%d}" / name,
        root / f"{when:%Y}" / name,
        root / f"{when:%Y%m%d}" / name,
        root / name,
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(name)


def gfs_path(root: Path, cycle: datetime, fhour: int) -> Path:
    hour = f"{cycle:%H}"
    cycle_dir = root / f"{cycle:%Y}" / f"gfs.{cycle:%Y%m%d%H}"
    candidates = [
        cycle_dir / f"gfs.t{hour}z.pgrb2.0p50.f{fhour:03d}",
        cycle_dir / f"gfs.t{hour}z.pgrb2.1p00.f{fhour:03d}",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"GFS f{fhour:03d} in {cycle_dir}")


def build_history(args) -> None:
    start = datetime.strptime(args.start_date, "%Y%m%d")
    year_start = datetime(start.year, 1, 1) + timedelta(days=args.history_start_doy)
    last_history = start - timedelta(days=1)
    fnl_root = Path(args.fnl_root)
    out_root = Path(args.out_root) / "ERA5" / f"{start.year}"
    previous_mean: pd.DataFrame | None = None
    missing_records: list[str] = []
    for day in date_range(year_start, last_history):
        out_dir = out_root / f"{day:%Y%m%d}"
        existing = read_daily_mean(out_dir)
        if existing is not None:
            previous_mean = existing
            print(f"history {day:%Y%m%d} cached")
            continue
        frames = []
        for hour in (0, 6, 12, 18):
            when = day.replace(hour=hour)
            try:
                grib = fnl_path(fnl_root, when)
            except FileNotFoundError as exc:
                record = f"history missing {when:%Y%m%d%H} {exc}"
                missing_records.append(record)
                print(record)
                continue
            try:
                lat, lon, t2 = extract_t2_c(args.wgrib2, grib)
            except Exception as exc:
                record = f"history unreadable {when:%Y%m%d%H} {grib} {exc}"
                missing_records.append(record)
                print(record)
                continue
            frames.append(interpolate_to_target(args, lat, lon, t2))
        if not frames and previous_mean is not None:
            record = f"history fill_previous_day {day:%Y%m%d}"
            missing_records.append(record)
            print(record)
            frames.append(previous_mean)
        previous_mean = write_daily_mean(frames, out_dir)
        print(f"history {day:%Y%m%d} frames={len(frames)}")
    append_missing_report(out_root, missing_records)


def build_forecast(args) -> None:
    start = datetime.strptime(args.start_date, "%Y%m%d")
    cycle = datetime.strptime(args.gfs_cycle, "%Y%m%d%H") if args.gfs_cycle else (start - timedelta(days=1)).replace(hour=12)
    gfs_root = Path(args.gfs_root)
    grouped: dict[str, list[pd.DataFrame]] = defaultdict(list)
    missing_records: list[str] = []
    end = start + timedelta(days=args.predict_days)
    max_hour = int((end.replace(hour=23) - cycle).total_seconds() // 3600)
    for fhour in range(0, max_hour + 1, 3):
        valid = cycle + timedelta(hours=fhour)
        if valid.date() < start.date() or valid.date() > end.date():
            continue
        try:
            grib = gfs_path(gfs_root, cycle, fhour)
        except FileNotFoundError as exc:
            record = f"forecast missing {valid:%Y%m%d%H} f{fhour:03d} {exc}"
            missing_records.append(record)
            print(record)
            continue
        try:
            lat, lon, t2 = extract_t2_c(args.wgrib2, grib)
        except Exception as exc:
            record = f"forecast unreadable {valid:%Y%m%d%H} f{fhour:03d} {grib} {exc}"
            missing_records.append(record)
            print(record)
            continue
        grouped[f"{valid:%Y%m%d}"].append(interpolate_to_target(args, lat, lon, t2))
    out_root = Path(args.out_root) / "GFS" / f"{start.year}" / f"{start:%Y%m%d}"
    previous_mean: pd.DataFrame | None = None
    expected_days = [(start + timedelta(days=offset)).strftime("%Y%m%d") for offset in range(args.predict_days + 1)]
    for day_key in expected_days:
        out_dir = out_root / day_key
        existing = read_daily_mean(out_dir)
        if existing is not None:
            previous_mean = existing
            print(f"forecast {day_key} cached")
        elif day_key in grouped:
            previous_mean = write_daily_mean(grouped[day_key], out_dir)
            print(f"forecast {day_key} frames={len(grouped[day_key])}")
        elif previous_mean is not None:
            record = f"forecast fill_previous_day {day_key}"
            missing_records.append(record)
            print(record)
            previous_mean = write_daily_mean([previous_mean], out_dir)
    append_missing_report(out_root, missing_records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--predict-days", type=int, required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--fnl-root", default="/g1/COMMONDATA/glob/fnl")
    parser.add_argument("--gfs-root", default="/g1/COMMONDATA/glob/gfs")
    parser.add_argument("--gfs-cycle")
    parser.add_argument("--history-start-doy", type=int, default=154)
    parser.add_argument("--wgrib2", default="/g1/app/mathlib/wgrib2/2.0.6/intel/bin/wgrib2")
    parser.add_argument("--skip-history", action="store_true")
    parser.add_argument("--skip-forecast", action="store_true")
    parser.add_argument("--lat-min", type=float, default=35.0)
    parser.add_argument("--lat-max", type=float, default=45.0)
    parser.add_argument("--lon-min", type=float, default=111.0)
    parser.add_argument("--lon-max", type=float, default=121.0)
    parser.add_argument("--resolution", type=float, default=0.1)
    args = parser.parse_args()
    if not args.skip_history:
        build_history(args)
    if not args.skip_forecast:
        build_forecast(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
