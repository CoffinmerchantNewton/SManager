#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent

CHUNKS = [
    ("20240701", "20240721", 20),
    ("20240721", "20240810", 20),
    ("20240810", "20240830", 20),
    ("20240830", "20240919", 20),
    ("20240919", "20241001", 12),
]

BASE_ENV = {
    "FLOWCTL": "/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/flowctl.py",
    "LIJT_BIN": "/g7/anxq/Zhangjt/workspace/Smanager/auto-lijt-pollen/bin",
    "WRFCHEMI_FLOW_BIN": "/g7/anxq/Zhangjt/workspace/Smanager/auto-wrfchem-pollen/bin",
    "ENV_SCRIPT": "/g7/anxq/Zhangjt/workspace/load_env.sh",
    "PYTHON_BIN": "/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python",
    "FNL_ROOTS": "/g1/COMMONDATA/glob/fnl:/g7/anxq/Zhangjt/static/fnl",
    "FNL_MIN_MB": "5",
    "LIJT_SOURCE_ROOT": "/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre3",
    "LIJT_PROGRAM_REL": "program/run_met_sh-2024",
    "LIJT_WPS_REL": "WRF-pollen1/WPS-master",
    "LIJT_WRF_REL": "WRF-pollen1/WRF-pollen_Tot_Arte_Chen/test/em_real",
    "LIJT_FNL_GFS": "2",
    "LIJT_WRF_PARTITION": "normal",
    "LIJT_WRF_NTASKS": "384",
    "LIJT_WRF_NTASKS_PER_NODE": "32",
    "LIJT_WRF_WALLTIME": "72:00:00",
    "LIJT_TIME_STEP": "180",
    "AREA": "Neimeng",
    "WRFCHEMI_DOMAIN": "d01",
    "POLLEN_LAT_MIN": "35.0",
    "POLLEN_LAT_MAX": "50.0",
    "POLLEN_LON_MIN": "95.0",
    "POLLEN_LON_MAX": "125.0",
    "POLLEN_GRID_RES": "0.1",
    "TEMPERATURE_LAT_MIN": "35.0",
    "TEMPERATURE_LAT_MAX": "50.0",
    "TEMPERATURE_LON_MIN": "95.0",
    "TEMPERATURE_LON_MAX": "125.0",
    "TEMPERATURE_GRID_RES": "0.1",
    "WRFCHEMI_N_JOBS": "16",
    "PARAM_ROOT": "/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/Autumn_phenological_model_DATA/DOY_optimal_parameters",
    "PFT_FILE": "/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Plant_function_type_CLM.nc",
    "EF_ROOT": "/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/ef_DL_history/ef_surface/ef_surface_2d",
    "EF_CHEN_ROOT": "/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/ef_DL_history-Chenopods_0p3/ef_surface/ef_surface_2d",
    "MEIC_DIR": "/g7/anxq/Zhangjt/workspace/pollen_forcast/meic-2017-0p25-RADM2",
}

BASE_CONFIG = {
    "node_order": [
        "prepare_case",
        "wps_fnl",
        "wps_gfs",
        "real",
        "generate_wrfchemi",
        "wrf_run",
        "postprocess",
    ],
    "env": BASE_ENV,
    "slurm_defaults": {
        "partition": "normal",
        "nodes": 1,
        "ntasks": 32,
        "cpus_per_task": 1,
        "walltime": "02:00:00",
    },
    "nodes": {
        "prepare_case": {
            "command": "bash \"$LIJT_BIN/prepare_case.sh\"",
            "slurm": {"walltime": "03:00:00"},
        },
        "wps_fnl": {
            "command": "bash \"$LIJT_BIN/run_wps_fnl.sh\"",
            "slurm": {"walltime": "03:00:00"},
        },
        "wps_gfs": {
            "command": "bash \"$LIJT_BIN/run_wps_gfs.sh\"",
            "slurm": {"walltime": "03:00:00"},
        },
        "real": {
            "command": "bash \"$LIJT_BIN/run_real.sh\"",
            "env": {"REAL_COMMAND": "run_lijt_real"},
            "slurm": {"nodes": 2, "ntasks": 64, "walltime": "02:00:00"},
        },
        "generate_wrfchemi": {
            "command": "bash \"$LIJT_BIN/generate_wrfchemi.sh\"",
            "slurm": {"nodes": 1, "ntasks": 32, "walltime": "12:00:00"},
        },
        "wrf_run": {
            "command": "bash \"$LIJT_BIN/run_wrf.sh\"",
            "env": {"WRF_RUN_COMMAND": "run_lijt_wrf"},
            "slurm": {"nodes": 12, "ntasks": 384, "walltime": "72:00:00"},
        },
        "postprocess": {
            "command": "bash \"$LIJT_BIN/postprocess.sh\"",
            "slurm": {"walltime": "00:30:00"},
        },
    },
}


def main() -> int:
    for start, end, days in CHUNKS:
        config = copy.deepcopy(BASE_CONFIG)
        config["env"]["LIJT_START_DATE"] = start
        config["env"]["LIJT_PREDICT_DAYS"] = str(days)
        config["env"]["LIJT_WRFCHEM_NAME"] = f"lijt_nm_{start}_{end}"
        path = ROOT / f"commands.lijt_hybrid_neimeng_{start}_{end}.json"
        path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
