#!/usr/bin/env bash
set -euo pipefail

START_DATE=${START_DATE:?START_DATE is required}
PREDICT_DAYS=${PREDICT_DAYS:-7}
RUN_DIR=${RUN_DIR:?RUN_DIR is required}
WRF_DIR=${WRF_DIR:-$RUN_DIR/WRF}
WRFCHEMI_DIR=${WRFCHEMI_DIR:-$RUN_DIR/wrfchemi}
JOB_NAME=${JOB_NAME:-WRFNEW}
NTASKS=${NTASKS:-576}

sim_start=$(date -d "$START_DATE -2 days" +%Y%m%d)
yyyy=${sim_start:0:4}
mm=${sim_start:4:2}
dd=${sim_start:6:2}

cd "$WRF_DIR"
rm -f wrfchemi_d01_* wrfout_d01_* wrfrst_d01_* rsl.error.* rsl.out.* ./*.err ./*.out
src="$WRFCHEMI_DIR/wrfchemi_d01_${yyyy}-${mm}-${dd}_12_00_00.nc"
dst="wrfchemi_d01_${yyyy}-${mm}-${dd}_12:00:00"
test -f "$src"
ln -sf "$src" "$dst"

mkdir -p "$RUN_DIR/logs" "$RUN_DIR/wrfout"
cat > run_wrfchem.sbatch <<EOF
#!/bin/bash
#SBATCH --comment=WRF
#SBATCH -J $JOB_NAME
#SBATCH -p normal
#SBATCH -n $NTASKS
#SBATCH --ntasks-per-node=32
#SBATCH -t 10:00:00
#SBATCH -o $RUN_DIR/logs/wrfchem_%j.out
#SBATCH -e $RUN_DIR/logs/wrfchem_%j.err

module load compiler/intel/composer_xe_2017.2.174
module load mpi/intelmpi/2017.2.174
module load mathlib/hdf/4.2.13/intel
module load mathlib/netcdf/4.4.0/intel
module load mathlib/ncl_ncarg/6.4.0/gnu
cd "$WRF_DIR"
mpirun ./wrf.exe
EOF

job_id=$(sbatch --parsable run_wrfchem.sbatch)
echo "$job_id" > "$RUN_DIR/wrfchem_job_id.txt"
echo "submitted wrfchem job $job_id"
