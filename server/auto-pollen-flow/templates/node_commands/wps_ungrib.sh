#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

echo "[wps_ungrib] TODO: replace this template with ungrib command wiring"
echo "[wps_ungrib] RUN_ID=${RUN_ID:-}"
