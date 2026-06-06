#!/usr/bin/env bash
set -euo pipefail

RUN_DIR=${RUN_DIR:?RUN_DIR is required}
REF_WPS=${REF_WPS:-/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre3/WPS_met_save_data/WPS-master5}
REF_WRF=${REF_WRF:-/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre3/WRF-pollen1/WRF-pollen_Tot_Arte_Chen/test/em_real}
REF_WRF_MAIN=${REF_WRF_MAIN:-/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre3/WRF-pollen1/WRF-pollen_Tot_Arte_Chen/main}

WPS_DIR="$RUN_DIR/WPS"
WRF_DIR="$RUN_DIR/WRF"
mkdir -p "$RUN_DIR"

if [[ ! -d "$WPS_DIR" ]]; then
  mkdir -p "$WPS_DIR"
  rsync -a \
    --exclude 'data/***' \
    --exclude 'GFS_FNL_FILE_SAVE/***' \
    --exclude 'FILE:*' \
    --exclude 'GRIBFILE.*' \
    --exclude 'met_em.*' \
    --exclude '*.log' \
    "$REF_WPS"/ "$WPS_DIR"/
  mkdir -p "$WPS_DIR/data/fnl" "$WPS_DIR/data/gfs" "$WPS_DIR/GFS_FNL_FILE_SAVE/fnl" "$WPS_DIR/GFS_FNL_FILE_SAVE/gfs"
fi

if [[ ! -d "$WRF_DIR" ]]; then
  mkdir -p "$WRF_DIR"
  rsync -a \
    --exclude 'met_em.*' \
    --exclude 'wrfinput*' \
    --exclude 'wrfbdy*' \
    --exclude 'wrfout*' \
    --exclude 'wrfrst*' \
    --exclude 'wrfchemi*' \
    --exclude 'rsl.*' \
    --exclude '*.out' \
    --exclude '*.err' \
    "$REF_WRF"/ "$WRF_DIR"/
fi

rm -f "$WRF_DIR/wrfinput"* "$WRF_DIR/wrfbdy"* "$WRF_DIR/real.exe" "$WRF_DIR/wrf.exe"
ln -sf "$REF_WRF_MAIN/real.exe" "$WRF_DIR/real.exe"
ln -sf "$REF_WRF_MAIN/wrf.exe" "$WRF_DIR/wrf.exe"

echo "WPS_DIR=$WPS_DIR"
echo "WRF_DIR=$WRF_DIR"
