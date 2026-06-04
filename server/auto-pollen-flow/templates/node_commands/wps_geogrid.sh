#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

echo "[wps_geogrid] TODO: replace this template with geogrid command wiring"
echo "[wps_geogrid] RUN_ID=${RUN_ID:-}"
