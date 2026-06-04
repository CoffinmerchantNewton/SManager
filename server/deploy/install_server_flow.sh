#!/bin/bash
set -eo pipefail

ROOT="${1:-$(pwd)}"

mkdir -p \
  "${ROOT}/runs" \
  "${ROOT}/node_commands" \
  "${ROOT}/logs" \
  "${ROOT}/products"

if [ -d "${ROOT}/templates/node_commands" ] && [ ! -f "${ROOT}/node_commands/common.sh" ]; then
  cp "${ROOT}/templates/node_commands/"*.sh "${ROOT}/node_commands/"
  chmod +x "${ROOT}/node_commands/"*.sh
fi

chmod +x "${ROOT}/flowctl.py"

echo "Installed server flow runtime under ${ROOT}"
echo "Edit ${ROOT}/templates/run_spec/commands.auto_pollen.example.json before production submit."
