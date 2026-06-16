#!/usr/bin/env bash
set -euo pipefail

FLOW_ROOT=${FLOW_ROOT:-/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow}
PY=${PY:-/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python}
CMD_DIR=${CMD_DIR:-/g7/anxq/Zhangjt/workspace/Smanager/auto-lijt-pollen/manual_neimeng_240701_241001}
DRY_RUN=${DRY_RUN:-false}

runs=(
  lijt_hybrid_neimeng_20240701_20240721
  lijt_hybrid_neimeng_20240721_20240810
  lijt_hybrid_neimeng_20240810_20240830
  lijt_hybrid_neimeng_20240830_20240919
  lijt_hybrid_neimeng_20240919_20241001
)

starts=(
  2024-07-01T12:00:00
  2024-07-21T12:00:00
  2024-08-10T12:00:00
  2024-08-30T12:00:00
  2024-09-19T12:00:00
)

ends=(
  2024-07-21T12:00:00
  2024-08-10T12:00:00
  2024-08-30T12:00:00
  2024-09-19T12:00:00
  2024-10-01T12:00:00
)

commands=(
  commands.lijt_hybrid_neimeng_20240701_20240721.json
  commands.lijt_hybrid_neimeng_20240721_20240810.json
  commands.lijt_hybrid_neimeng_20240810_20240830.json
  commands.lijt_hybrid_neimeng_20240830_20240919.json
  commands.lijt_hybrid_neimeng_20240919_20241001.json
)

cd "$FLOW_ROOT"

for idx in "${!runs[@]}"; do
  command_file="$CMD_DIR/${commands[$idx]}"
  echo "[preflight] ${commands[$idx]}"
  "$PY" flowctl.py preflight --commands-file "$command_file"
done

for idx in "${!runs[@]}"; do
  echo "[plan] ${runs[$idx]}"
  "$PY" flowctl.py plan \
    --run-id "${runs[$idx]}" \
    --start "${starts[$idx]}" \
    --end "${ends[$idx]}" \
    --period autumn \
    --domain neimeng \
    --variant lijt_hybrid \
    --met-provider fnl_gfs \
    --commands-file "$CMD_DIR/${commands[$idx]}"
done

for run_id in "${runs[@]}"; do
  echo "[submit] ${run_id}"
  if [ "$DRY_RUN" = "true" ]; then
    "$PY" flowctl.py submit --run-id "$run_id" --dry-run
  else
    "$PY" flowctl.py submit --run-id "$run_id"
  fi
done
