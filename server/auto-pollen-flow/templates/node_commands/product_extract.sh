#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

echo "[product_extract] TODO: replace this template with product extraction command"
echo "[product_extract] RUN_ID=${RUN_ID:-}"
