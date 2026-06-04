#!/bin/bash
set -eo pipefail

require_var() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "[node-command] required env var is missing: ${name}" >&2
    exit 2
  fi
}

source_env_if_present() {
  if [ -n "${ENV_SCRIPT:-}" ] && [ -f "${ENV_SCRIPT}" ]; then
    set +u
    # shellcheck source=/dev/null
    source "${ENV_SCRIPT}"
    set -u
  fi
}

run_in_auto_pollen() {
  require_var AUTO_POLLEN_ROOT
  cd "${AUTO_POLLEN_ROOT}"
  "$@"
}
