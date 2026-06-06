#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
load_case_env

wrfchemi_flow_bin=${WRFCHEMI_FLOW_BIN:-/g7/anxq/Zhangjt/workspace/Smanager/auto-wrfchem-pollen/bin}
test -x "${wrfchemi_flow_bin}/run_wrfchemi_chain.sh" || fail "wrfchemi chain not executable: ${wrfchemi_flow_bin}/run_wrfchemi_chain.sh"
test -s "${LIJT_WRF_DIR}/wrfinput_d01" || fail "wrfinput_d01 missing, run real first"

RUN_DIR="${FLOW_RUN_DIR}" \
FLOW_BIN="${wrfchemi_flow_bin}" \
CASE_WRF_DIR="${LIJT_WRF_DIR}" \
START_DATE="${LIJT_START_DATE}" \
PREDICT_DAYS="${LIJT_PREDICT_DAYS}" \
WRFCHEMI_DIR="${FLOW_RUN_DIR}/wrfchemi/" \
bash "${wrfchemi_flow_bin}/run_wrfchemi_chain.sh"

target="${FLOW_RUN_DIR}/wrfchemi/wrfchemi_d01_$(run_start_nc_name).nc"
test -s "${target}" || fail "generated wrfchemi is missing: ${target}"
cp -f "${target}" "${LIJT_WRFCHEMI_SAVE_PATH}/$(basename "${target}")"
echo "[generate_wrfchemi] ${target}"
