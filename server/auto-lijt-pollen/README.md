# Lijt WRFChem pollen flow

This package wires Lijt's `/g7/anxq/pollen_predict` WRF-pollen cases into
`auto-pollen-flow` without using the default `compute_gdd` node.

The Lijt scripts do not have a standalone Zhangjt-style `compute_gdd` step.
For Smanager the pollen/temperature/chemistry preparation is represented as
`generate_wrfchemi`, whose contract is to create:

```text
wrfchemi_d01_YYYY-MM-DD_12_00_00.nc
```

The run order is configured by `node_order` in the commands file:

```text
prepare_case -> wps_fnl -> wps_gfs -> real -> generate_wrfchemi -> wrf_run
```

`prepare_case` copies the selected Lijt case into the Smanager run directory
before any script mutates `namelist.*`, links data, or removes temporary files.
This keeps the original `/g7/anxq/pollen_predict` tree untouched.

## 2025-08-15 Beijing autumn pre7

```bash
cd /g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow

/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python flowctl.py plan \
  --run-id lijt_bj_20250815_pre7 \
  --start 2025-08-15T12:00:00 \
  --end 2025-08-22T12:00:00 \
  --period 7d \
  --domain beijing \
  --variant lijt_autumn_pre7 \
  --met-provider fnl_gfs \
  --commands-file ../auto-lijt-pollen/commands.lijt_beijing_20250815_pre7.json

/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python flowctl.py preflight \
  --commands-file ../auto-lijt-pollen/commands.lijt_beijing_20250815_pre7.json

/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python flowctl.py submit \
  --run-id lijt_bj_20250815_pre7
```

## Multi-year Beijing autumn pre7 runs

Each target date needs its own commands file because `LIJT_START_DATE` is read
by the Lijt node scripts at runtime. Do not change only the `flowctl plan`
`--start/--end` values while reusing a commands file for another date.

Prepared commands files:

```text
commands.lijt_beijing_20250815_pre7.json
commands.lijt_beijing_20240815_pre7.json
commands.lijt_beijing_20230815_pre7.json
```

Use run IDs in this form when submitting through Smanager:

```text
lijt_bj_YYYY0815_pre7_smanager
```
