#!/usr/bin/env bash
set -euo pipefail

START_DATE=${START_DATE:?START_DATE is required, e.g. 20250815}
PREDICT_DAYS=${PREDICT_DAYS:-7}
RUN_DIR=${RUN_DIR:?RUN_DIR is required}
FNL_ROOT=${FNL_ROOT:-/g1/COMMONDATA/glob/fnl}
WPS_DIR=${WPS_DIR:-$RUN_DIR/WPS}
WPS_GEOG_DATA=${WPS_GEOG_DATA:-/g7/anxq/pollen_predict/WPS-geog_data}

start_time=$(date -d "$START_DATE -2 days" +"%Y-%m-%d_12:00:00")
end_time=$(date -d "$START_DATE +$PREDICT_DAYS days" +"%Y-%m-%d_12:00:00")
first_day=$(date -d "$START_DATE -2 days" +"%Y%m%d")
last_day=$(date -d "$START_DATE +$PREDICT_DAYS days" +"%Y%m%d")

module load compiler/intel/composer_xe_2017.2.174
module load mpi/intelmpi/2017.2.174
module load mathlib/hdf/4.2.13/intel
module load mathlib/netcdf/4.4.0/intel

cd "$WPS_DIR"
rm -f GRIBFILE.* FILE:* met_em.d01.* met_em.d02.* met_em.d03.* Vtable
rm -rf data/fnl
mkdir -p data/fnl

current="$first_day"
while [[ "$current" -le "$last_day" ]]; do
  year=${current:0:4}
  for hh in 00 06 12 18; do
    file="fnl_${current}_${hh}_00.grib2"
    for candidate in \
      "$FNL_ROOT/$year/$current/$file" \
      "$FNL_ROOT/$year/$file" \
      "$FNL_ROOT/$current/$file" \
      "$FNL_ROOT/$file"; do
      if [[ -f "$candidate" ]]; then
        ln -sf "$candidate" "data/fnl/$file"
        break
      fi
    done
  done
  current=$(date -d "$current +1 day" +%Y%m%d)
done

missing=0
current="$first_day"
while [[ "$current" -le "$last_day" ]]; do
  for hh in 00 06 12 18; do
    ts="${current}_${hh}"
    dt=$(date -d "${current} ${hh}:00" +"%Y-%m-%d_%H:00:00")
    if [[ "$dt" < "$start_time" || "$dt" > "$end_time" ]]; then
      continue
    fi
    if [[ ! -e "data/fnl/fnl_${current}_${hh}_00.grib2" ]]; then
      echo "missing FNL $ts" >&2
      missing=1
    fi
  done
  current=$(date -d "$current +1 day" +%Y%m%d)
done
if [[ "$missing" -ne 0 ]]; then
  exit 2
fi

sed -i "s/start_date = '.*',/start_date = '$start_time',/" namelist.wps
sed -i "s/end_date   = '.*',/end_date   = '$end_time',/" namelist.wps
sed -i "s|fg_name *=.*|fg_name = 'FILE',|" namelist.wps
sed -i "s|geog_data_path *=.*|geog_data_path = '$WPS_GEOG_DATA'|" namelist.wps
ln -sf /g7/anxq/Lijt/houqing-WRFChem/soa-ncp2/WPS/ungrib/Variable_Tables/Vtable.new Vtable

./link_grib.csh data/fnl/*
./geogrid.exe > geogrid.log 2>&1
tail -n 5 geogrid.log
./ungrib.exe > ungrib.log 2>&1
tail -n 5 ungrib.log
./metgrid.exe > metgrid.log 2>&1
tail -n 5 metgrid.log

out_dir="$RUN_DIR/met_em"
rm -rf "$out_dir"
mkdir -p "$out_dir"
mv met_em.d01.* "$out_dir"/
echo "$out_dir" > "$RUN_DIR/met_em_dir.txt"
echo "met_em written to $out_dir"
