#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

echo "[postprocess_eval] TODO: replace this template with evaluation command"
echo "[postprocess_eval] RUN_ID=${RUN_ID:-}"
