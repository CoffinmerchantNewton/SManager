#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

require_var RUN_ID
require_var FLOW_RUN_DIR

run_configured_command "real" "REAL_COMMAND" "${REAL_CWD:-${WRF_RUN_DIR:-${FLOW_RUN_DIR}}}"
