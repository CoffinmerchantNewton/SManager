#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
load_case_env

test -n "$(find "${FLOW_RUN_DIR}/wrfout" -maxdepth 1 -name 'wrfout_d01_*' -print -quit)" || fail "wrfout files are missing"
test -n "$(find "${FLOW_RUN_DIR}/wrfchemi" -maxdepth 1 -name 'wrfchemi_d01_*.nc' -print -quit)" || fail "wrfchemi file is missing"

{
  echo "start_date=${LIJT_START_DATE}"
  echo "predict_days=${LIJT_PREDICT_DAYS}"
  echo "case_root=${LIJT_CASE_ROOT}"
  echo "wrf_dir=${LIJT_WRF_DIR}"
  echo "wrf_job_id=$(cat "${FLOW_RUN_DIR}/lijt_wrf_job_id.txt" 2>/dev/null || true)"
  echo "wrfout_count=$(find "${FLOW_RUN_DIR}/wrfout" -maxdepth 1 -name 'wrfout_d01_*' | wc -l)"
  echo "wrfchemi=$(find "${FLOW_RUN_DIR}/wrfchemi" -maxdepth 1 -name 'wrfchemi_d01_*.nc' -print -quit)"
} > "${FLOW_RUN_DIR}/lijt_summary.txt"

cat "${FLOW_RUN_DIR}/lijt_summary.txt"
