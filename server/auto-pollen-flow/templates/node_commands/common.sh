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

run_configured_command() {
  local node="$1"
  local command_var="$2"
  local cwd="$3"
  local command="${!command_var:-}"
  if [ -z "${command}" ]; then
    echo "[${node}] required command env var is missing: ${command_var}" >&2
    exit 2
  fi
  if [ -z "${cwd}" ]; then
    cwd="${FLOW_RUN_DIR:-$PWD}"
  fi
  if [ ! -d "${cwd}" ]; then
    echo "[${node}] working directory does not exist: ${cwd}" >&2
    exit 2
  fi
  echo "[${node}] cwd=${cwd}"
  echo "[${node}] command=${command}"
  cd "${cwd}"
  bash -lc "${command}"
}
