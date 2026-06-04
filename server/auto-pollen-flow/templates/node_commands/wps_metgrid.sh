#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

echo "[wps_metgrid] TODO: replace this template with metgrid command wiring"
echo "[wps_metgrid] RUN_ID=${RUN_ID:-}"
