#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

echo "[compute_gdd] TODO: replace this template with compute_gdd.py execution"
echo "[compute_gdd] RUN_ID=${RUN_ID:-}"
