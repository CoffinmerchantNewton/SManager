#!/usr/bin/env bash
set -eo pipefail

fail() {
  echo "[auto-lijt-pollen] $*" >&2
  exit 2
}

require_var() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    fail "required env var is missing: ${name}"
  fi
}

run_start_date() {
  date -d "${LIJT_START_DATE} -2 days" +"%Y%m%d"
}

run_start_stamp() {
  date -d "$(run_start_date)" +"%Y-%m-%d_12:00:00"
}

run_end_stamp() {
  date -d "${LIJT_START_DATE} +${LIJT_PREDICT_DAYS} days" +"%Y-%m-%d_12:00:00"
}

run_start_nc_name() {
  date -d "$(run_start_date)" +"%Y-%m-%d_12_00_00"
}

run_start_link_name() {
  date -d "$(run_start_date)" +"%Y-%m-%d_12:00:00"
}

load_case_env() {
  require_var FLOW_RUN_DIR
  local env_file="${FLOW_RUN_DIR}/lijt_case.env"
  if [ ! -f "${env_file}" ]; then
    fail "case env not found, run prepare_case first: ${env_file}"
  fi
  # shellcheck source=/dev/null
  source "${env_file}"
}

source_env_if_present() {
  if [ -n "${ENV_SCRIPT:-}" ] && [ -f "${ENV_SCRIPT}" ]; then
    set +u
    # shellcheck source=/dev/null
    source "${ENV_SCRIPT}"
    set -u
  fi
}

load_lijt_runtime_modules() {
  if command -v module >/dev/null 2>&1; then
    module load compiler/intel/composer_xe_2017.2.174
    module load mpi/intelmpi/2017.2.174
    module load mathlib/hdf/4.2.13/intel
    module load mathlib/netcdf/4.4.0/intel
    module load mathlib/ncl_ncarg/6.4.0/gnu
  fi
  export LD_LIBRARY_PATH="/g1/app/mathlib/jasper/1.701.0/intel/lib:${LD_LIBRARY_PATH:-}"
}

configure_wrf_namelist() {
  local namelist="$1"
  local start_date year month day end_date end_year end_month end_day levels
  local met_dir first_met e_we e_sn
  start_date=$(run_start_date)
  year="${start_date:0:4}"
  month="${start_date:4:2}"
  day="${start_date:6:2}"
  end_date=$(date -d "${LIJT_START_DATE} +${LIJT_PREDICT_DAYS} days" +"%Y%m%d")
  end_year="${end_date:0:4}"
  end_month="${end_date:4:2}"
  end_day="${end_date:6:2}"

  sed -i "s/run_days                 = [0-9]*,/run_days                 = $((LIJT_PREDICT_DAYS + 2)),/" "${namelist}"
  sed -i "s/start_year               = [0-9]*,/start_year               = ${year},/" "${namelist}"
  sed -i "s/start_month              = [0-9]*,/start_month              = ${month},/" "${namelist}"
  sed -i "s/start_day                = [0-9]*,/start_day                = ${day},/" "${namelist}"
  sed -i "s/start_hour               = [0-9]*,/start_hour               = 12,/" "${namelist}"
  sed -i "s/end_year                 = [0-9]*,/end_year                 = ${end_year},/" "${namelist}"
  sed -i "s/end_month                = [0-9]*,/end_month                = ${end_month},/" "${namelist}"
  sed -i "s/end_day                  = [0-9]*,/end_day                  = ${end_day},/" "${namelist}"
  sed -i "s/end_hour                 = [0-9]*,/end_hour                 = 12,/" "${namelist}"
  if [ -n "${LIJT_TIME_STEP:-}" ]; then
    sed -i "s/time_step                = [0-9]*/time_step                = ${LIJT_TIME_STEP}/" "${namelist}"
  fi

  met_dir="${LIJT_MET_SAVE_PATH:-}/${LIJT_START_DATE:-}"
  if [ -d "${met_dir}" ] && command -v ncdump >/dev/null 2>&1; then
    first_met=$(find "${met_dir}" -maxdepth 1 -name 'met_em.d01.*.nc' | sort | head -n 1)
    if [ -n "${first_met}" ]; then
      e_we=$(ncdump -h "${first_met}" | awk -F= '/WEST-EAST_GRID_DIMENSION/ {gsub(/[^0-9]/, "", $2); print $2; exit}')
      e_sn=$(ncdump -h "${first_met}" | awk -F= '/SOUTH-NORTH_GRID_DIMENSION/ {gsub(/[^0-9]/, "", $2); print $2; exit}')
      if [ -n "${e_we}" ] && [ -n "${e_sn}" ]; then
        sed -i -E "s/(e_we[[:space:]]*=[[:space:]]*)[0-9]+(,.*)/\1${e_we}\2/" "${namelist}"
        sed -i -E "s/(e_sn[[:space:]]*=[[:space:]]*)[0-9]+(,.*)/\1${e_sn}\2/" "${namelist}"
      fi
    fi
  fi

  if [ "${year:2:2}" -le 16 ]; then
    levels=27
  elif [ "${year:2:2}" -le 19 ]; then
    levels=32
  else
    levels=34
  fi
  sed -i "s/num_metgrid_levels       = [0-9]*/num_metgrid_levels       = ${levels}/" "${namelist}"
}
