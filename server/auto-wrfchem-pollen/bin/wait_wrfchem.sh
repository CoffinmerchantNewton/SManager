#!/usr/bin/env bash
set -euo pipefail

RUN_DIR=${RUN_DIR:?RUN_DIR is required}
WRF_DIR=${WRF_DIR:-$RUN_DIR/WRF}
INTERVAL=${INTERVAL:-300}

job_file="$RUN_DIR/wrfchem_job_id.txt"
test -f "$job_file"
job_id=$(cat "$job_file")

while squeue -j "$job_id" -h | grep -q .; do
  echo "[$(date '+%F %T')] WRF-Chem job $job_id still running"
  sleep "$INTERVAL"
done

if [[ ! -f "$WRF_DIR/rsl.error.0000" ]]; then
  echo "missing rsl.error.0000" >&2
  exit 2
fi

tail -n 40 "$WRF_DIR/rsl.error.0000"
if ! tail -n 5 "$WRF_DIR/rsl.error.0000" | grep -q SUCCESS; then
  echo "WRF-Chem did not finish with SUCCESS" >&2
  exit 3
fi

mkdir -p "$RUN_DIR/wrfout"
find "$WRF_DIR" -maxdepth 1 -type f -name 'wrfout_d01_*' -exec mv {} "$RUN_DIR/wrfout"/ \;
echo "wrfout moved to $RUN_DIR/wrfout"
