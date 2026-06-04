#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

echo "[prep_pollen] TODO: replace this template with prep_pollen_data.py execution"
echo "[prep_pollen] RUN_ID=${RUN_ID:-}"
