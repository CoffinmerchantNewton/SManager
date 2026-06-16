#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_var FLOW_RUN_DIR
require_var LIJT_SOURCE_ROOT
require_var LIJT_WPS_REL
require_var LIJT_WRF_REL

LIJT_START_DATE=${LIJT_START_DATE:-20250815}
LIJT_PREDICT_DAYS=${LIJT_PREDICT_DAYS:-7}
LIJT_FNL_GFS=${LIJT_FNL_GFS:-2}
LIJT_PROGRAM_REL=${LIJT_PROGRAM_REL:-program}
case_name=${LIJT_CASE_NAME:-$(basename "${LIJT_SOURCE_ROOT}")}
case_root=${LIJT_CASE_ROOT:-${FLOW_RUN_DIR}/case/${case_name}}
wps_top=${LIJT_WPS_REL%%/*}
wrf_top=${LIJT_WRF_REL%%/*}

[ -d "${LIJT_SOURCE_ROOT}" ] || fail "Lijt source root does not exist: ${LIJT_SOURCE_ROOT}"
mkdir -p "${FLOW_RUN_DIR}/case"

if [ ! -d "${case_root}/program" ]; then
  mkdir -p "${case_root}"
  cp -a --reflink=auto "${LIJT_SOURCE_ROOT}/program" "${case_root}/program"
fi

for top in "${wps_top}" "${wrf_top}"; do
  [ -n "${top}" ] || continue
  [ "${top}" = "." ] && continue
  [ "${top}" = "program" ] && continue
  if [ ! -d "${case_root}/${top}" ]; then
    [ -d "${LIJT_SOURCE_ROOT}/${top}" ] || fail "Lijt top-level dir missing: ${LIJT_SOURCE_ROOT}/${top}"
    cp -a --reflink=auto "${LIJT_SOURCE_ROOT}/${top}" "${case_root}/${top}"
  fi
done

lijt_wps_dir="${case_root}/${LIJT_WPS_REL}"
lijt_wrf_dir="${case_root}/${LIJT_WRF_REL}"
lijt_program_dir="${case_root}/${LIJT_PROGRAM_REL}"
[ -d "${lijt_wps_dir}" ] || fail "copied WPS dir missing: ${lijt_wps_dir}"
[ -d "${lijt_wrf_dir}" ] || fail "copied WRF run dir missing: ${lijt_wrf_dir}"
[ -d "${lijt_program_dir}" ] || fail "copied program dir missing: ${lijt_program_dir}"

geog_data_path=${LIJT_GEOG_DATA_PATH:-/g7/anxq/pollen_predict/WPS-geog_data}
[ -d "${geog_data_path}" ] || fail "WPS geog data path missing: ${geog_data_path}"
sed -i -E "s|geog_data_path = '.*'|geog_data_path = '${geog_data_path}'|" "${lijt_wps_dir}/namelist.wps"

year=${LIJT_START_DATE:0:4}
met_save_path="${case_root}/WPS_met_save_data/pre${LIJT_PREDICT_DAYS}days_12-12_${LIJT_FNL_GFS}/${year}"
wrfchemi_save_path="${case_root}/WPS_met_save_data/wrfchemi_data_12-12_pre${LIJT_PREDICT_DAYS}/${year}"
mkdir -p "${met_save_path}/${LIJT_START_DATE}" "${wrfchemi_save_path}" "${FLOW_RUN_DIR}/wrfchemi" "${FLOW_RUN_DIR}/wrfout"

if [ "${LIJT_PURGE_RUNTIME:-0}" = "1" ]; then
  find "${lijt_wrf_dir}" -maxdepth 1 \( -name 'met_em.d01.*' -o -name 'wrfchemi_d01_*' -o -name 'wrfout_d01_*' -o -name 'wrfrst_d01_*' -o -name 'rsl.*' -o -name '*.err' -o -name '*.out' \) -delete
fi

cat > "${FLOW_RUN_DIR}/lijt_case.env" <<EOF
LIJT_SOURCE_ROOT="${LIJT_SOURCE_ROOT}"
LIJT_CASE_ROOT="${case_root}"
LIJT_PROGRAM_REL="${LIJT_PROGRAM_REL}"
LIJT_PROGRAM_DIR="${lijt_program_dir}"
LIJT_WPS_DIR="${lijt_wps_dir}"
LIJT_WRF_DIR="${lijt_wrf_dir}"
LIJT_MET_SAVE_PATH="${met_save_path}"
LIJT_WRFCHEMI_SAVE_PATH="${wrfchemi_save_path}"
LIJT_START_DATE="${LIJT_START_DATE}"
LIJT_PREDICT_DAYS="${LIJT_PREDICT_DAYS}"
LIJT_FNL_GFS="${LIJT_FNL_GFS}"
LIJT_WRFCHEM_NAME="${LIJT_WRFCHEM_NAME:-poll_lijt_smgr}"
LIJT_TIME_STEP="${LIJT_TIME_STEP:-}"
AREA="${AREA:-Beijing}"
WRFCHEMI_DOMAIN="${WRFCHEMI_DOMAIN:-d01}"
POLLEN_LAT_MIN="${POLLEN_LAT_MIN:-}"
POLLEN_LAT_MAX="${POLLEN_LAT_MAX:-}"
POLLEN_LON_MIN="${POLLEN_LON_MIN:-}"
POLLEN_LON_MAX="${POLLEN_LON_MAX:-}"
POLLEN_GRID_RES="${POLLEN_GRID_RES:-}"
EOF

echo "${case_root}" > "${FLOW_RUN_DIR}/lijt_case_root.txt"
echo "${lijt_wrf_dir}" > "${FLOW_RUN_DIR}/lijt_wrf_dir.txt"
echo "${met_save_path}" > "${FLOW_RUN_DIR}/met_em_dir.txt"
echo "[prepare_case] case_root=${case_root}"
