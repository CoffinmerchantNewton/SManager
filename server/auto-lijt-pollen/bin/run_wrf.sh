#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
load_case_env

met_dir="${LIJT_MET_SAVE_PATH}/${LIJT_START_DATE}"
wrfchemi_nc="${FLOW_RUN_DIR}/wrfchemi/wrfchemi_d01_$(run_start_nc_name).nc"
test -s "${wrfchemi_nc}" || fail "wrfchemi missing: ${wrfchemi_nc}"

cd "${LIJT_WRF_DIR}"
rm -f met_em.d01.* wrfchemi_d01_* wrfout_d01_* rsl.* *.err *.out
ln -sf "${met_dir}"/met_em.d01.* .
ln -sf "${wrfchemi_nc}" "wrfchemi_d01_$(run_start_link_name)"
configure_wrf_namelist "${LIJT_WRF_DIR}/namelist.input"

job_name=${LIJT_WRFCHEM_NAME:-poll_lijt_smgr}
cat > runwrf.smanager.sbatch <<EOF
#!/bin/bash
#SBATCH --comment=WRF
#SBATCH -J ${job_name}
#SBATCH -p ${LIJT_WRF_PARTITION:-normal}
#SBATCH -n ${LIJT_WRF_NTASKS:-256}
#SBATCH --ntasks-per-node=${LIJT_WRF_NTASKS_PER_NODE:-32}
#SBATCH -t ${LIJT_WRF_WALLTIME:-7:00:00}
#SBATCH -o ${FLOW_RUN_DIR}/logs/lijt_wrf_%j.out
#SBATCH -e ${FLOW_RUN_DIR}/logs/lijt_wrf_%j.err

module load compiler/intel/composer_xe_2017.2.174
module load mpi/intelmpi/2017.2.174
module load mathlib/hdf/4.2.13/intel
module load mathlib/netcdf/4.4.0/intel
module load mathlib/ncl_ncarg/6.4.0/gnu

date
mpirun ./wrf.exe
EOF

job_id=$(sbatch --parsable runwrf.smanager.sbatch | cut -d ';' -f 1)
echo "${job_id}" > "${FLOW_RUN_DIR}/lijt_wrf_job_id.txt"
echo "[wrf_run] submitted ${job_id} (${job_name})"

while squeue -j "${job_id}" -h >/dev/null 2>&1 && [ -n "$(squeue -j "${job_id}" -h)" ]; do
  date "+[wrf_run] %Y-%m-%d %H:%M:%S still running job=${job_id}"
  sleep 300
done

if [ ! -f rsl.error.0000 ]; then
  fail "rsl.error.0000 not found after WRF"
fi
tail -n 20 rsl.error.0000
tail -n 1 rsl.error.0000 | grep -q SUCCESS || fail "WRF did not finish with SUCCESS"

mkdir -p "${FLOW_RUN_DIR}/wrfout"
cp -f wrfout_d01_* "${FLOW_RUN_DIR}/wrfout/"
echo "[wrf_run] wrfout copied to ${FLOW_RUN_DIR}/wrfout"
