#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def load_catalog(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_symlink(link: Path, target: str) -> None:
    if link.exists() or link.is_symlink():
        if link.is_symlink() and os.readlink(link) == target:
            return
        if link.is_dir() and not link.is_symlink():
            shutil.rmtree(link)
        else:
            link.unlink()
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        raise SystemExit(f"target already exists: {dst}")
    shutil.copytree(src, dst, symlinks=True)


def write_batch_run(path: Path) -> None:
    path.write_text("""#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CASE_ENV="${CASE_ENV:-${PROJECT_ROOT}/case.env}"
RUN_STEP="${PROJECT_ROOT}/scripts/run_step.sh"

usage() {
  cat <<'EOF'
usage:
  bash batch_run.sh all
  bash batch_run.sh wps_fnl
  bash batch_run.sh wps_gfs
  bash batch_run.sh real
  bash batch_run.sh generate_wrfchemi
  bash batch_run.sh wrf_run
  bash batch_run.sh postprocess

说明:
  这个目录是完整手工工作包。WPS、WRF、emission、logs、output 都在本目录下。
EOF
}

step="${1:-all}"
case "${step}" in
  all)
    for s in wps_fnl wps_gfs real generate_wrfchemi wrf_run postprocess; do
      bash "${RUN_STEP}" "${CASE_ENV}" "${s}"
    done
    ;;
  wps_fnl|wps_gfs|real|generate_wrfchemi|wrf_run|postprocess)
    bash "${RUN_STEP}" "${CASE_ENV}" "${step}"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    exit 2
    ;;
esac
""", encoding="utf-8")
    path.chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage a full manual Lijt work package")
    parser.add_argument("--catalog", default=str(Path(__file__).resolve().parents[1] / "catalog.json"))
    parser.add_argument("--profile", required=True)
    parser.add_argument("--case-dir", required=True)
    parser.add_argument("--start-date", required=True, help="YYYYMMDD")
    parser.add_argument("--predict-days", required=True, type=int)
    parser.add_argument("--fnl-gfs", default="2")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    catalog = load_catalog(Path(args.catalog))
    common = catalog.get("common", {})
    profile = catalog.get("profiles", {}).get(args.profile)
    if not profile:
        raise SystemExit(f"profile not found: {args.profile}")
    if not profile.get("available", False):
        raise SystemExit(profile.get("note", f"profile unavailable: {args.profile}"))

    case_dir = Path(args.case_dir).expanduser().resolve()
    source_root = Path(profile["source_root"])
    static_dir = case_dir / "static"
    if args.force and case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)

    wps_src = source_root / profile["wps_rel"]
    wrf_src = source_root / profile["wrf_rel"]
    program_src = source_root / "program"
    emission_src = Path(profile.get("emission_model_dir", ""))
    for src in (wps_src, wrf_src, program_src, emission_src):
        if not src.exists():
            raise SystemExit(f"missing source subtree: {src}")

    # The staged case is intentionally a full manual working package, not a
    # light run directory. Users can copy this case elsewhere and edit in place.
    copy_tree(wps_src, case_dir / "WPS")
    copy_tree(wrf_src, case_dir / "WRF")
    copy_tree(program_src, case_dir / "program")
    copy_tree(emission_src, case_dir / "emission")

    scripts_dir = case_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for helper in ("run_step.sh", "manual_run_all.sh"):
        src = Path(__file__).resolve().parent / helper
        dst = scripts_dir / helper
        shutil.copy2(src, dst)
        dst.chmod(0o755)

    # Empty runtime folders live beside the staged template.
    for rel in ("output", "output/wps_met", "output/wrfchemi", "output/wrfout", "logs", "cache", "temperature", "pollen_flux", "wrfchemi_meic"):
        (case_dir / rel).mkdir(parents=True, exist_ok=True)

    static_dir.mkdir(parents=True, exist_ok=True)
    static_map = {
        "wps_geog_data": common.get("LIJT_GEOG_DATA_PATH", "/g7/anxq/pollen_predict/WPS-geog_data"),
        "fnl_primary": "/g1/COMMONDATA/glob/fnl",
        "fnl_fallback": "/g7/anxq/Zhangjt/static/fnl",
        "meic_dir": common.get("MEIC_DIR", ""),
        "emission_model_dir": profile.get("emission_model_dir", ""),
    }
    for key, value in profile.get("model_env", {}).items():
        if value:
            static_map[key.lower()] = value

    # Link only the paths we actually want to hand around.
    link_keys = [
        "wps_geog_data",
        "fnl_primary",
        "fnl_fallback",
        "meic_dir",
        "emission_model_dir",
        "param_root",
        "pft_file",
        "ef_root",
        "ef_chen_root",
        "temperature_model_root",
    ]
    for key in link_keys:
        target = static_map.get(key)
        if target:
            ensure_symlink(static_dir / key, target)

    year = args.start_date[:4]
    met_save_path = case_dir / "output" / "wps_met" / f"pre{args.predict_days}days_12-12_{args.fnl_gfs}" / year
    wrfchemi_save_path = case_dir / "output" / "wrfchemi" / f"pre{args.predict_days}days_12-12" / year
    met_save_path.mkdir(parents=True, exist_ok=True)
    wrfchemi_save_path.mkdir(parents=True, exist_ok=True)

    case_env = {
        "FLOW_RUN_DIR": str(case_dir),
        "LIJT_SOURCE_ROOT": str(source_root),
        "LIJT_CASE_ROOT": str(case_dir),
        "LIJT_PROGRAM_REL": profile["program_rel"],
        "LIJT_PROGRAM_DIR": str(case_dir / profile["program_rel"]),
        "LIJT_WPS_DIR": str(case_dir / "WPS"),
        "LIJT_WRF_DIR": str(case_dir / "WRF"),
        "LIJT_MET_SAVE_PATH": str(met_save_path),
        "LIJT_WRFCHEMI_SAVE_PATH": str(wrfchemi_save_path),
        "LIJT_START_DATE": args.start_date,
        "LIJT_PREDICT_DAYS": str(args.predict_days),
        "LIJT_FNL_GFS": str(args.fnl_gfs),
        "LIJT_WRFCHEM_NAME": f"{args.profile}_{args.start_date}_{args.predict_days}d",
        "LIJT_TIME_STEP": "180",
        "AREA": profile["region"],
        "WRFCHEMI_DOMAIN": "d01",
        "LIJT_BIN": common.get("LIJT_BIN", "/g7/anxq/Zhangjt/workspace/Smanager/auto-lijt-pollen/bin"),
        "WRFCHEMI_FLOW_BIN": common.get("WRFCHEMI_FLOW_BIN", "/g7/anxq/Zhangjt/workspace/Smanager/auto-wrfchem-pollen/bin"),
        "ENV_SCRIPT": common.get("ENV_SCRIPT", "/g7/anxq/Zhangjt/workspace/load_env.sh"),
        "PYTHON_BIN": common.get("PYTHON_BIN", "/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python"),
        "FNL_ROOTS": common.get("FNL_ROOTS", "/g1/COMMONDATA/glob/fnl:/g7/anxq/Zhangjt/static/fnl"),
        "LIJT_GEOG_DATA_PATH": str(static_dir / "wps_geog_data"),
        "MEIC_DIR": str(static_dir / "meic_dir"),
        "TEMP_ROOT": str(case_dir / "temperature"),
        "POLLEN_DIR": str(case_dir / "pollen_flux"),
        "MEIC_SAVE_DIR": str(case_dir / "wrfchemi_meic"),
        "WRFCHEMI_DIR": str(case_dir / "output" / "wrfchemi"),
        "CACHE_DIR": str(case_dir / "cache"),
        "CASE_WRF_DIR": str(case_dir / "WRF"),
    }
    case_env.update({k: str(v) for k, v in profile.get("model_env", {}).items() if v})
    case_env["PARAM_ROOT"] = str(static_dir / "param_root")
    case_env["PFT_FILE"] = str(static_dir / "pft_file")
    case_env["EF_ROOT"] = str(static_dir / "ef_root")
    case_env["EF_CHEN_ROOT"] = str(static_dir / "ef_chen_root")
    case_env["TEMPERATURE_MODEL_ROOT"] = str(static_dir / "temperature_model_root")
    case_env["EMISSION_MODEL_DIR"] = str(case_dir / "emission")
    case_env["EMISSION_RUN_SCRIPT"] = profile.get("emission_run_script", "")

    lines = [f'{k}="{v}"' for k, v in case_env.items() if v]
    (case_dir / "case.env").write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.copyfile(case_dir / "case.env", case_dir / "lijt_case.env")

    manifest = {
        "profile": args.profile,
        "source_root": str(source_root),
        "case_root": str(case_dir),
        "wps_dir": str(case_dir / "WPS"),
        "wrf_dir": str(case_dir / "WRF"),
        "program_dir": str(case_dir / "program"),
        "emission_dir": str(case_dir / "emission"),
        "static_dir": str(static_dir),
        "emission_model_dir": profile.get("emission_model_dir", ""),
        "emission_run_script": profile.get("emission_run_script", ""),
    }
    (case_dir / "stage_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_batch_run(case_dir / "batch_run.sh")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
