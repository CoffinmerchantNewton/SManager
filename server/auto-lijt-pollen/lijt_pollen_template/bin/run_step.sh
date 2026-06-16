#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: run_step.sh [case.env] <step>" >&2
  exit 2
}

if [ $# -lt 1 ]; then
  usage
fi

case_env=""
if [ -f "$1" ]; then
  case_env="$1"
  shift
else
  case_env="${CASE_ENV:-$(pwd)/case.env}"
fi

step="${1:-}"
[ -n "${step}" ] || usage
[ -f "${case_env}" ] || { echo "missing case env: ${case_env}" >&2; exit 2; }

set -a
source "${case_env}"
set +a

case "${step}" in
  wps_fnl) bash "${LIJT_BIN}/run_wps_fnl.sh" ;;
  wps_gfs) bash "${LIJT_BIN}/run_wps_gfs.sh" ;;
  real) bash "${LIJT_BIN}/run_real.sh" ;;
  generate_wrfchemi) bash "${LIJT_BIN}/generate_wrfchemi.sh" ;;
  wrf_run) bash "${LIJT_BIN}/run_wrf.sh" ;;
  postprocess) bash "${LIJT_BIN}/postprocess.sh" ;;
  *)
    echo "unknown step: ${step}" >&2
    exit 2
    ;;
esac
