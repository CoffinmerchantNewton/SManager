#!/bin/bash
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
source_env_if_present

mkdir -p "${FLOW_RUN_DIR}/products"
cat > "${FLOW_RUN_DIR}/products/product_manifest.json" <<EOF
{
  "run_id": "${RUN_ID}",
  "products": []
}
EOF
echo "[package_products] wrote empty product manifest for ${RUN_ID}"
