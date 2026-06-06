#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
load_case_env
load_lijt_runtime_modules

cd "${LIJT_PROGRAM_DIR}"
./auto_run_wps_GFS.sh "${LIJT_START_DATE}" "${LIJT_CASE_ROOT}" "${LIJT_WPS_DIR}" "${LIJT_PREDICT_DAYS}" "${LIJT_FNL_GFS}" "${LIJT_MET_SAVE_PATH}"

test -n "$(find "${LIJT_MET_SAVE_PATH}/${LIJT_START_DATE}" -maxdepth 1 -name 'met_em.d01.*' -print -quit)"
echo "[wps_gfs] met_em saved in ${LIJT_MET_SAVE_PATH}/${LIJT_START_DATE}"
