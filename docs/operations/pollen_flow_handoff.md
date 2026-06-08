# Pollen forecast handoff notes

Last updated: 2026-06-08

This note summarizes the Lijt Beijing WRF-Chem pollen work, the Zhangjt
Neimeng auto-pollen run, and the operational issues found while wiring them
through SManager.

Do not put server passwords in this file. Use the local SManager `.env`, saved
CLI token, or operator-provided SSH credentials.

## Workspace And Server Roots

Local working tree:

```text
E:\SManager
```

Remote SManager workdir:

```text
/g7/anxq/Zhangjt/workspace/Smanager
```

Remote Lijt project root:

```text
/g7/anxq/pollen_predict
```

Remote Zhangjt Neimeng auto-pollen root:

```text
/g7/anxq/Zhangjt/workspace/auto-pollen
```

SManager server flow root:

```text
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow
```

The server-side Python used for flow control is:

```text
/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python
```

## What Was Done In This Session

1. Lijt Beijing WRF-Chem pollen flow was inspected and wired into SManager as a
   separate flow under `server/auto-lijt-pollen/`.
2. Two Lijt Beijing historical pre7 tasks were planned/submitted, then later
   cancelled at the user's request:

```text
lijt_bj_20240815_pre7_smanager
lijt_bj_20230815_pre7_smanager
```

3. A Neimeng Zhangjt auto-pollen run was created for:

```text
2024-07-01 00:00 UTC -> 2024-10-01 00:00 UTC
```

That 92-day run was later cancelled because the business forecast products need
to appear sooner and the queue wall-time risk was too high. The current
operational submission is split into three independent monthly runs:

```text
2024070100_2024080100_autumn_neimeng_official
2024080100_2024090100_autumn_neimeng_official
2024090100_2024100100_autumn_neimeng_official
```

This split may introduce small month-boundary spin-up differences, which were
accepted for the current business-product priority.

4. Five missing public FNL files were downloaded from NCAR/RDA THREDDS and
   uploaded to:

```text
/g7/anxq/Zhangjt/static/fnl/2024
```

Missing cycles repaired:

```text
fnl_20240917_00_00.grib2
fnl_20240917_06_00.grib2
fnl_20240917_12_00.grib2
fnl_20240925_18_00.grib2
fnl_20240926_00_00.grib2
```

Public source pattern:

```text
https://thredds.rda.ucar.edu/thredds/fileServer/files/g/d083002/grib2/2024/2024.09/<file>
```

5. Remote `auto-pollen/scripts/copy_fnl.py` was patched so standard 00/06/12/18
   cycles are always considered even when the primary daily FNL directory
   exists but is incomplete.
6. SManager state handling was patched so re-planning an existing run resets
   stale node status, `error_code`, `started_at`, and `finished_at`.
7. SManager WRF progress detection was patched to include variant-suffixed
   output directories such as `wrf24070100-24100100_official`.
8. Git commit created:

```text
8499b13 Add Neimeng 20240701 pollen run spec
```

## Lijt Beijing WRF-Chem Pollen Flow

Lijt's project is under:

```text
/g7/anxq/pollen_predict
```

Important rule: do not mix Zhangjt `auto-pollen/compute_gdd.py` into the Lijt
Beijing WRF-Chem pollen workflow unless a Lijt script explicitly calls an
equivalent step. These are different projects.

The Lijt SManager package is:

```text
server/auto-lijt-pollen/
```

Prepared commands files:

```text
server/auto-lijt-pollen/commands.lijt_beijing_20250815_pre7.json
server/auto-lijt-pollen/commands.lijt_beijing_20240815_pre7.json
server/auto-lijt-pollen/commands.lijt_beijing_20230815_pre7.json
```

Lijt run order in SManager:

```text
prepare_case
wps_fnl
wps_gfs
real
generate_wrfchemi
wrf_run
postprocess
product_extract
package_products
```

The Lijt `generate_wrfchemi` node is the replacement for a separate GDD-style
node in this SManager decomposition. It is expected to generate date-bound
WRF-Chem emissions/pollen input such as:

```text
wrfchemi_d01_YYYY-MM-DD_12_00_00.nc
```

Date caution: each Lijt historical run needs a matching commands file because
`LIJT_START_DATE` is read by node scripts at runtime. Do not change only
`flowctl plan --start/--end` while reusing a commands file for another year.

Known status from this session:

```text
lijt_bj_20240815_pre7_smanager
  Cancelled after prepare_case/wps/real/generate_wrfchemi had succeeded.
  Later wrf_run/postprocess/product nodes were cancelled.

lijt_bj_20230815_pre7_smanager
  Cancelled after wps_gfs failed/was stopped.
```

This means the Lijt flow has been analyzed and partially exercised, but not yet
fully proven from zero inputs through final SManager web products.

## Neimeng Zhangjt Auto-Pollen Flow

Reference domain requested by the user:

```text
/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf23071700-23091600
```

Reference WPS namelist values:

```text
max_dom = 2
e_we = 103, 247
e_sn = 83, 208
dx = 27000
dy = 27000
ref_lat = 44.997
ref_lon = 108.698
truelat1 = 42.999
truelat2 = 42.999
stand_lon = 112.646
i_parent_start = 1, 16
j_parent_start = 1, 9
parent_grid_ratio = 1, 3
```

The active date-specific SManager commands files are:

```text
server/auto-pollen-flow/templates/run_spec/commands.auto_pollen.neimeng_20240701_20240801.json
server/auto-pollen-flow/templates/run_spec/commands.auto_pollen.neimeng_20240801_20240901.json
server/auto-pollen-flow/templates/run_spec/commands.auto_pollen.neimeng_20240901_20241001.json
```

Remote deployed path:

```text
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/templates/run_spec/commands.auto_pollen.neimeng_20240701_20240801.json
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/templates/run_spec/commands.auto_pollen.neimeng_20240801_20240901.json
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/templates/run_spec/commands.auto_pollen.neimeng_20240901_20241001.json
```

Current run ids:

```text
2024070100_2024080100_autumn_neimeng_official
2024080100_2024090100_autumn_neimeng_official
2024090100_2024100100_autumn_neimeng_official
```

Current output directories:

```text
/g7/anxq/Zhangjt/workspace/auto-pollen/WPS/wps24070100-24080100
/g7/anxq/Zhangjt/workspace/auto-pollen/WPS/wps24080100-24090100
/g7/anxq/Zhangjt/workspace/auto-pollen/WPS/wps24090100-24100100
/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf24070100-24080100_official
/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf24080100-24090100_official
/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf24090100-24100100_official
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/2024070100_2024080100_autumn_neimeng_official
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/2024080100_2024090100_autumn_neimeng_official
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/2024090100_2024100100_autumn_neimeng_official
```

Active Slurm chain at the time this note was written:

```text
2024070100_2024080100_autumn_neimeng_official:
  20653489 fnl_verify        success
  20653490 wps_geogrid       pending/running after dependency release
  20653491 wrf_setup         pending, afterok dependency
  20653492 wrf_run           pending, afterok dependency
  20653493 postprocess_eval  pending, afterok dependency
  20653494 product_extract   pending, afterok dependency
  20653495 package_products  pending, afterok dependency

2024080100_2024090100_autumn_neimeng_official:
  20653497 fnl_verify
  20653498 wps_geogrid
  20653499 wrf_setup
  20653500 wrf_run
  20653501 postprocess_eval
  20653502 product_extract
  20653503 package_products

2024090100_2024100100_autumn_neimeng_official:
  20653506 fnl_verify
  20653507 wps_geogrid
  20653508 wrf_setup
  20653509 wrf_run
  20653510 postprocess_eval
  20653511 product_extract
  20653512 package_products
```

Verified before submitting the monthly runs:

```text
All three monthly commands files passed local and remote JSON validation.
All three monthly commands files passed SManager preflight.
The monthly target WPS/WRF/static FNL directories were absent before submit.
The old 92-day run was cancelled through SManager and no pollen Slurm jobs from it remained queued.
```

## Useful Commands

Local SManager CLI:

```powershell
cd E:\SManager
python packages\cli\smanager.py doctor
python packages\cli\smanager.py preflight --commands-file /g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/templates/run_spec/commands.auto_pollen.neimeng_20240701_20240801.json
python packages\cli\smanager.py status --run-id 2024070100_2024080100_autumn_neimeng_official
python packages\cli\smanager.py logs --run-id 2024070100_2024080100_autumn_neimeng_official --node wps_geogrid --tail 200
python packages\cli\smanager.py diagnose --run-id 2024070100_2024080100_autumn_neimeng_official
```

Server-side status without the local API:

```bash
cd /g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow
/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python flowctl.py status --run-id 2024070100_2024080100_autumn_neimeng_official --json
/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python flowctl.py logs --run-id 2024070100_2024080100_autumn_neimeng_official --node wps_geogrid --tail 200
squeue -u anxq -o '%i|%j|%T|%M|%l|%D|%R'
```

Plan and submit a monthly Neimeng run:

```powershell
cd E:\SManager
python packages\cli\smanager.py plan `
  --run-id 2024070100_2024080100_autumn_neimeng_official `
  --start 2024070100 `
  --end 2024080100 `
  --period autumn `
  --domain neimeng `
  --variant official `
  --met-provider FNL `
  --commands-file /g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/templates/run_spec/commands.auto_pollen.neimeng_20240701_20240801.json

python packages\cli\smanager.py submit --run-id 2024070100_2024080100_autumn_neimeng_official --dry-run
python packages\cli\smanager.py submit --run-id 2024070100_2024080100_autumn_neimeng_official
```

Cancel safely:

```powershell
python packages\cli\smanager.py cancel-run --run-id 2024070100_2024080100_autumn_neimeng_official --dry-run
python packages\cli\smanager.py cancel-run --run-id 2024070100_2024080100_autumn_neimeng_official --real
```

If there are inner or stale Slurm jobs, inspect before cancelling:

```bash
squeue -u anxq -o '%i|%j|%T|%M|%l|%D|%R'
```

Do not cancel unrelated jobs such as generic `WRFIMG2` or `WRFIMG3` unless you
have evidence they belong to the run being cleaned.

## Pitfalls Found

### Lijt and Zhangjt flows are different

Lijt Beijing WRF-Chem pollen should not use Zhangjt `compute_gdd.py` by default.
The user explicitly corrected this. Keep Lijt's own scripts as the source of
truth, especially `total_auto_run` style scripts under `/g7/anxq/pollen_predict`.

### SManager production commands may be stale for auto-pollen

The generic production commands originally pointed at shared directories like:

```text
/g7/anxq/Zhangjt/workspace/auto-pollen/run
```

and to script paths that were missing in that layout. For the Neimeng historical
run, the safer approach was to call:

```bash
auto_wrf.py --start 2024070100 --end 2024100100 --period autumn --tree-map-order official --max-dom 2
```

This creates isolated WPS/WRF directories:

```text
WPS/wps24070100-24100100
WRF/wrf24070100-24100100_official
```

### `tree-map-order official` changes WRF directory name

With `--tree-map-order official`, `auto_wrf.py` sets a run suffix and writes:

```text
wrf24070100-24100100_official
```

not:

```text
wrf24070100-24100100
```

Make sure `wrf_run`, `postprocess_eval`, `PRODUCT_SOURCE_GLOB`, and progress
detection all use the `_official` directory.

### FNL verification can use the wrong roots if called through the API

The local backend `.env` had:

```text
SERVER_FNL_ROOTS=/g7/anxq/Zhangjt/workspace/Smanager/fnl
```

That caused API-level `fnl-verify` to report the 2024 historical FNL as missing.
The actual commands file for this run uses:

```text
FNL_ROOTS=/g1/COMMONDATA/glob/fnl:/g7/anxq/Zhangjt/static/fnl
```

For authoritative verification, run the node through the server run spec or
inspect the run's `fnl_manifest.json`.

### Primary FNL day directory can be incomplete

`copy_fnl.py` previously listed only files that existed in the primary daily
directory when that directory existed. If the primary directory was missing
some cycles, fallback files were ignored. This caused 366 links instead of 372.

The patched copy stored in this repo is:

```text
server/auto-pollen-flow/remote_overrides/auto-pollen/scripts/copy_fnl.py
```

It was deployed to:

```text
/g7/anxq/Zhangjt/workspace/auto-pollen/scripts/copy_fnl.py
```

Expected behavior: for each day, consider the union of primary filenames and
the four standard FNL cycles:

```text
00, 06, 12, 18
```

### Slurm requires full 32-core node occupancy

Submitting lightweight jobs with only a few tasks can fail with:

```text
Node resource are not fully occupied by job
```

Use at least:

```text
nodes = 1
ntasks = 32
cpus_per_task = 1
```

For `real`, WRF setup, and `wrf_run`, this run uses:

```text
nodes = 2
ntasks = 64
cpus_per_task = 1
```

### Re-planning an existing run used to leave stale state

Before the patch, `flowctl plan` did not reset existing node status files. A
run could show new Slurm job IDs while keeping stale `run_cancelled` or old
`node_command_failed` fields. The patched `state.py` resets nodes during plan
and clears stale terminal fields when a node becomes `ready` or `running`.

### Do not let duplicate WPS jobs write the same directory

Several failed/partial submit attempts left duplicate `pollen_wps_geogrid` jobs.
When cleaning, cancel the whole active dependency chain and any stale duplicate
WPS job, then remove only this run's target directories:

```text
/g7/anxq/Zhangjt/workspace/auto-pollen/WPS/wps24070100-24080100
/g7/anxq/Zhangjt/workspace/auto-pollen/WPS/wps24080100-24090100
/g7/anxq/Zhangjt/workspace/auto-pollen/WPS/wps24090100-24100100
/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf24070100-24080100_official
/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf24080100-24090100_official
/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf24090100-24100100_official
/g7/anxq/Zhangjt/workspace/auto-pollen/static/fnl24070100-24080100
/g7/anxq/Zhangjt/workspace/auto-pollen/static/fnl24080100-24090100
/g7/anxq/Zhangjt/workspace/auto-pollen/static/fnl24090100-24100100
```

Verify exact paths before `rm -rf`.

The cancelled 92-day run left partial output under:

```text
/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf24070100-24100100_official
```

That path is separate from the monthly runs. Do not delete it unless explicitly
asked, because it may still be useful for diagnosis.

### Local backend and web visibility

The local `SManagerMySQL` Windows service failed to start with service error
1053 during this session. To continue operating, a local FastAPI backend was
started with SQLite:

```text
DATABASE_URL=sqlite:///E:/SManager/backend/pollen_forecast.db
```

This made `backend/pollen_forecast.db` dirty locally. It was intentionally not
committed. If the web UI cannot see a run, check which backend database it is
using, whether the API is running, and whether products have been synced after
`package_products`.

## When Products Finish

After `package_products` succeeds, sync each monthly run into the local backend:

```powershell
cd E:\SManager
python packages\cli\smanager.py sync-products --run-id 2024070100_2024080100_autumn_neimeng_official
python packages\cli\smanager.py sync-products --run-id 2024080100_2024090100_autumn_neimeng_official
python packages\cli\smanager.py sync-products --run-id 2024090100_2024100100_autumn_neimeng_official
python packages\cli\smanager.py products --run-id 2024070100_2024080100_autumn_neimeng_official
python packages\cli\smanager.py products --run-id 2024080100_2024090100_autumn_neimeng_official
python packages\cli\smanager.py products --run-id 2024090100_2024100100_autumn_neimeng_official
```

Product metadata for these runs should include:

```text
PRODUCT_REGION=neimeng
PRODUCT_POLLEN_TYPE=pollen_total
PRODUCT_RESOLUTION=9km d02
PRODUCT_SOURCE_GLOB=/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf24070100-24080100_official/output/wrfout_d02_*
PRODUCT_SOURCE_GLOB=/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf24080100-24090100_official/output/wrfout_d02_*
PRODUCT_SOURCE_GLOB=/g7/anxq/Zhangjt/workspace/auto-pollen/WRF/wrf24090100-24100100_official/output/wrfout_d02_*
```

The summary product is configured as daily sampling from hourly/3-hourly WRF
outputs:

```text
PRODUCT_SUMMARY_MAX_STEPS=32 for July and August, 31 for September
PRODUCT_SUMMARY_EVERY_NTH=8
PRODUCT_SUMMARY_STEP_HOURS=24
```

Check the actual WRF output interval before interpreting this as daily output.

## What Is Fully Learned And What Is Not

Neimeng Zhangjt auto-pollen:

```text
The SManager submission path, FNL repair, WPS bootstrap, output paths, and main
pitfalls are understood and documented. The first 92-day attempt was cancelled
after reaching WRF because the business output needed faster partial delivery.
The current operational path is the three monthly Neimeng runs listed above.
They were planned, preflighted, submitted, and accepted by Slurm, but the final
monthly web products were not yet complete when this note was written.
```

Lijt Beijing WRF-Chem pollen:

```text
The rough full workflow and SManager decomposition are understood, and historical
run specs were created. However, the Lijt flow has not yet been proven end to
end through final web products in this session. Treat it as partially learned
and partially exercised, not fully taken over.
```

The next operator or AI should continue by monitoring the three active monthly
Neimeng runs, sync products after each `package_products`, then return to Lijt
Beijing if the goal is to completely take over that separate workflow.
