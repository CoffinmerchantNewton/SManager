#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

echo "[wrf_setup] TODO: replace this template with WRF run directory setup"
echo "[wrf_setup] FLOW_RUN_DIR=${FLOW_RUN_DIR:-}"
