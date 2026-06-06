#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
load_case_env
load_lijt_runtime_modules

met_dir="${LIJT_MET_SAVE_PATH}/${LIJT_START_DATE}"
test -n "$(find "${met_dir}" -maxdepth 1 -name 'met_em.d01.*' -print -quit)" || fail "met_em files are missing: ${met_dir}"

cd "${LIJT_WRF_DIR}"
rm -f met_em.d01.* wrfinput_d01 wrfbdy_d01 rsl.* real*.log
ln -sf "${met_dir}"/met_em.d01.* .
configure_wrf_namelist "${LIJT_WRF_DIR}/namelist.input"

./real.exe
tail -n 5 rsl.error.0000 || true
test -s wrfinput_d01
test -s wrfbdy_d01
echo "[real] wrfinput_d01 and wrfbdy_d01 are ready"
