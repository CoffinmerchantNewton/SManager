#!/usr/bin/env bash
set -euo pipefail

START_DATE=${START_DATE:?START_DATE is required}
PREDICT_DAYS=${PREDICT_DAYS:-7}
RUN_DIR=${RUN_DIR:?RUN_DIR is required}
ENV_SCRIPT=${ENV_SCRIPT:-/g7/anxq/Zhangjt/workspace/load_env.sh}
FLOW_BIN=${FLOW_BIN:-/g7/anxq/Zhangjt/workspace/Smanager/auto-wrfchem-pollen/bin}

TEMP_ROOT=${TEMP_ROOT:-$RUN_DIR/temperature}
POLLEN_DIR=${POLLEN_DIR:-$RUN_DIR/pollen_flux}
MEIC_SAVE_DIR=${MEIC_SAVE_DIR:-$RUN_DIR/wrfchemi_meic/}
WRFCHEMI_DIR=${WRFCHEMI_DIR:-$RUN_DIR/wrfchemi/}
CACHE_DIR=${CACHE_DIR:-$RUN_DIR/cache}
CASE_WRF_DIR=${CASE_WRF_DIR:-$RUN_DIR/WRF}
WRF_DIR=$CASE_WRF_DIR

AREA=${AREA:-Beijing}
WRFCHEMI_DOMAIN=${WRFCHEMI_DOMAIN:-d01}
POLLEN_LAT_MIN=${POLLEN_LAT_MIN:-35}
POLLEN_LAT_MAX=${POLLEN_LAT_MAX:-45}
POLLEN_LON_MIN=${POLLEN_LON_MIN:-111}
POLLEN_LON_MAX=${POLLEN_LON_MAX:-121}
POLLEN_GRID_RES=${POLLEN_GRID_RES:-0.1}
TEMPERATURE_LAT_MIN=${TEMPERATURE_LAT_MIN:-$POLLEN_LAT_MIN}
TEMPERATURE_LAT_MAX=${TEMPERATURE_LAT_MAX:-$POLLEN_LAT_MAX}
TEMPERATURE_LON_MIN=${TEMPERATURE_LON_MIN:-$POLLEN_LON_MIN}
TEMPERATURE_LON_MAX=${TEMPERATURE_LON_MAX:-$POLLEN_LON_MAX}
TEMPERATURE_GRID_RES=${TEMPERATURE_GRID_RES:-$POLLEN_GRID_RES}
WRFCHEMI_N_JOBS=${WRFCHEMI_N_JOBS:-8}

PARAM_ROOT=${PARAM_ROOT:-/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/Autumn_phenological_model_DATA/DOY_optimal_parameters}
PFT_FILE=${PFT_FILE:-/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Plant_function_type_CLM.nc}
EF_ROOT=${EF_ROOT:-/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/ef_DL_history/ef_surface/ef_surface_2d}
EF_CHEN_ROOT=${EF_CHEN_ROOT:-/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/ef_DL_history-Chenopods_0p3/ef_surface/ef_surface_2d}
MEIC_DIR=${MEIC_DIR:-/g7/anxq/Zhangjt/workspace/pollen_forcast/meic-2017-0p25-RADM2}

mkdir -p "$TEMP_ROOT" "$POLLEN_DIR" "$MEIC_SAVE_DIR" "$WRFCHEMI_DIR" "$CACHE_DIR/meic" "$CACHE_DIR/pollen"

if [[ -f "$ENV_SCRIPT" ]]; then
  # Provides wrfTool Python plus NetCDF/xarray/scipy dependencies for all Python preprocessing.
  set +u
  source "$ENV_SCRIPT"
  set -u
fi
WRF_DIR=$CASE_WRF_DIR
PYTHON_BIN=${PYTHON_BIN:-python}

"$PYTHON_BIN" "$FLOW_BIN/make_temperature_inputs.py" \
  --start-date "$START_DATE" \
  --predict-days "$PREDICT_DAYS" \
  --out-root "$TEMP_ROOT" \
  --lat-min "$TEMPERATURE_LAT_MIN" \
  --lat-max "$TEMPERATURE_LAT_MAX" \
  --lon-min "$TEMPERATURE_LON_MIN" \
  --lon-max "$TEMPERATURE_LON_MAX" \
  --resolution "$TEMPERATURE_GRID_RES"

"$PYTHON_BIN" "$FLOW_BIN/pollen_predict.py" \
  --start_date_str "$START_DATE" \
  --predict_days "$PREDICT_DAYS" \
  --pollen_emiss_path "$POLLEN_DIR" \
  --area "$AREA" \
  --param_root "$PARAM_ROOT" \
  --pft_file "$PFT_FILE" \
  --ef_root "$EF_ROOT" \
  --ef_chen_root "$EF_CHEN_ROOT" \
  --temp_root "$TEMP_ROOT" \
  --cache_dir "$CACHE_DIR/pollen" \
  --lat-min "$POLLEN_LAT_MIN" \
  --lat-max "$POLLEN_LAT_MAX" \
  --lon-min "$POLLEN_LON_MIN" \
  --lon-max "$POLLEN_LON_MAX" \
  --resolution "$POLLEN_GRID_RES"

"$PYTHON_BIN" "$FLOW_BIN/make_meic_wrfchemi.py" \
  --start_date_str "$START_DATE" \
  --predict_days "$PREDICT_DAYS" \
  --wrfinput_file "$WRF_DIR/wrfinput_d01" \
  --domain "$WRFCHEMI_DOMAIN" \
  --meic_save_dir "$MEIC_SAVE_DIR" \
  --meic_dir "$MEIC_DIR" \
  --cache_dir "$CACHE_DIR/meic" \
  --n_jobs "$WRFCHEMI_N_JOBS"

"$PYTHON_BIN" "$FLOW_BIN/add_pollen_to_wrfchemi.py" \
  --start_date_str "$START_DATE" \
  --predict_days "$PREDICT_DAYS" \
  --domain "$WRFCHEMI_DOMAIN" \
  --area "$AREA" \
  --pollen_emiss_path "$POLLEN_DIR" \
  --meic_save_dir "$MEIC_SAVE_DIR" \
  --meic_poll_save_dir "$WRFCHEMI_DIR"

echo "$WRFCHEMI_DIR" > "$RUN_DIR/wrfchemi_dir.txt"
ls -lh "$WRFCHEMI_DIR"
