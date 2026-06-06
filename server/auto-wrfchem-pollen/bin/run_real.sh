#!/usr/bin/env bash
set -euo pipefail

START_DATE=${START_DATE:?START_DATE is required}
PREDICT_DAYS=${PREDICT_DAYS:-7}
RUN_DIR=${RUN_DIR:?RUN_DIR is required}
WRF_DIR=${WRF_DIR:-$RUN_DIR/WRF}
MET_DIR=${MET_DIR:-$RUN_DIR/met_em}

module load compiler/intel/composer_xe_2017.2.174
module load mpi/intelmpi/2017.2.174
module load mathlib/hdf/4.2.13/intel
module load mathlib/netcdf/4.4.0/intel
module load mathlib/ncl_ncarg/6.4.0/gnu

sim_start=$(date -d "$START_DATE -2 days" +%Y%m%d)
sim_end=$(date -d "$START_DATE +$PREDICT_DAYS days" +%Y%m%d)
yyyy=${sim_start:0:4}
mm=${sim_start:4:2}
dd=${sim_start:6:2}
end_yyyy=${sim_end:0:4}
end_mm=${sim_end:4:2}
end_dd=${sim_end:6:2}

cd "$WRF_DIR"
rm -f met_em.d01.* wrfinput_d01 wrfbdy_d01 rsl.error.* rsl.out.*
ln -sf "$MET_DIR"/met_em.d01.* ./

sed -i "s/run_days                 = [0-9]*,/run_days                 = $((PREDICT_DAYS + 2)),/" namelist.input
sed -i "s/start_year               = [0-9]*/start_year               = $yyyy/" namelist.input
sed -i "s/start_month              = [0-9]*/start_month              = $mm/" namelist.input
sed -i "s/start_day                = [0-9]*/start_day                = $dd/" namelist.input
sed -i "s/start_hour               = [0-9]*/start_hour               = 12/" namelist.input
sed -i "s/end_year                 = [0-9]*/end_year                 = $end_yyyy/" namelist.input
sed -i "s/end_month                = [0-9]*/end_month                = $end_mm/" namelist.input
sed -i "s/end_day                  = [0-9]*/end_day                  = $end_dd/" namelist.input
sed -i "s/end_hour                 = [0-9]*/end_hour                 = 12/" namelist.input
sed -i "s/num_metgrid_levels       = [0-9]*/num_metgrid_levels       = 34/" namelist.input

./real.exe
tail -n 30 rsl.error.0000
test -f wrfinput_d01
test -f wrfbdy_d01
