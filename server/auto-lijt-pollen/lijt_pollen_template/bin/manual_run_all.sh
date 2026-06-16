#!/usr/bin/env bash
set -euo pipefail

case_env="${1:-${CASE_ENV:-$(pwd)/case.env}}"
shift || true

steps=(wps_fnl wps_gfs real generate_wrfchemi wrf_run postprocess)
for step in "${steps[@]}"; do
  bash "$(dirname "$0")/run_step.sh" "${case_env}" "${step}"
done
