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
ssh "${TARGET}" "chmod +x '${REMOTE_DIR}/flowctl.py' '${REMOTE_DIR}'/templates/node_commands/*.sh"

echo "Synced auto-pollen-flow to ${TARGET}:${REMOTE_DIR}"
