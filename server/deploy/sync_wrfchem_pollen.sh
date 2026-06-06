#!/bin/bash
set -eo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <ssh-target> <remote-dir>" >&2
  echo "Example: $0 anxq@10.40.140.17 /g7/anxq/Zhangjt/workspace/Smanager/auto-wrfchem-pollen" >&2
  exit 2
fi

TARGET="$1"
REMOTE_DIR="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC="${REPO_ROOT}/server/auto-wrfchem-pollen/"

ssh "${TARGET}" "mkdir -p '${REMOTE_DIR}'"
rsync -av --delete \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  "${SRC}" "${TARGET}:${REMOTE_DIR}/"
ssh "${TARGET}" "REMOTE_DIR='${REMOTE_DIR}' bash -s" <<'REMOTE_INSTALL'
set -eo pipefail
chmod +x "${REMOTE_DIR}/bin/"*.sh
REMOTE_INSTALL

echo "Synced auto-wrfchem-pollen to ${TARGET}:${REMOTE_DIR}"
