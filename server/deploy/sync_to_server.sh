#!/bin/bash
set -eo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <ssh-target> <remote-dir>" >&2
  echo "Example: $0 user@server /g7/anxq/Zhangjt/workspace/auto-pollen-flow" >&2
  exit 2
fi

TARGET="$1"
REMOTE_DIR="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC="${REPO_ROOT}/server/auto-pollen-flow/"

ssh "${TARGET}" "mkdir -p '${REMOTE_DIR}'"
rsync -av --delete \
  --exclude '__pycache__/' \
  --exclude 'runs/' \
  --exclude '*.pyc' \
  "${SRC}" "${TARGET}:${REMOTE_DIR}/"
ssh "${TARGET}" "REMOTE_DIR='${REMOTE_DIR}' bash -s" <<'REMOTE_INSTALL'
set -eo pipefail
mkdir -p \
  "${REMOTE_DIR}/runs" \
  "${REMOTE_DIR}/node_commands" \
  "${REMOTE_DIR}/logs" \
  "${REMOTE_DIR}/products"

if [ -d "${REMOTE_DIR}/templates/node_commands" ] && [ ! -f "${REMOTE_DIR}/node_commands/common.sh" ]; then
  cp "${REMOTE_DIR}/templates/node_commands/"*.sh "${REMOTE_DIR}/node_commands/"
fi

chmod +x "${REMOTE_DIR}/flowctl.py"
chmod +x "${REMOTE_DIR}/templates/node_commands/"*.sh
if compgen -G "${REMOTE_DIR}/node_commands/*.sh" > /dev/null; then
  chmod +x "${REMOTE_DIR}/node_commands/"*.sh
fi
REMOTE_INSTALL

echo "Synced and installed auto-pollen-flow to ${TARGET}:${REMOTE_DIR}"
