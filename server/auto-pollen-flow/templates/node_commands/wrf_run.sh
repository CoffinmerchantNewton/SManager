#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

echo "[wrf_run] TODO: replace this template with mpirun ./wrf.exe execution"
echo "[wrf_run] RUN_ID=${RUN_ID:-}"
