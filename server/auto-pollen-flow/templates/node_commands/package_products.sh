#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

find_tool() {
  local configured="$1"
  local name="$2"
  if [ -n "${configured}" ]; then
    echo "${configured}"
    return
  fi
  for candidate in "${SCRIPT_DIR}/../../tools/${name}" "${SCRIPT_DIR}/../tools/${name}"; do
    if [ -f "${candidate}" ]; then
      echo "${candidate}"
      return
    fi
  done
  echo "[package_products] cannot find ${name}; set PACKAGE_PRODUCTS_TOOL" >&2
  exit 2
}

require_var RUN_ID
require_var FLOW_RUN_DIR

TOOL="$(find_tool "${PACKAGE_PRODUCTS_TOOL:-}" "package_products.py")"
"${PYTHON_BIN:-python3}" "${TOOL}"
