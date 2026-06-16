# Lijt Hybrid Neimeng 2024-07-01 to 2024-10-01 Manual Runbook

This template is for the corrected hybrid experiment:

- region/domain target: Neimeng, following the 20240701-20241001 operational split
- pollen emission model: Lijt Beijing autumn model
- emission chain: temperature inputs + pollen flux + MEIC base + pollen into `wrfchemi`
- integration chain: Lijt WRF-Chem case, not Zhangjt `auto-pollen`
- products: intentionally omitted from this manual template

The previous monthly `commands.auto_pollen.neimeng_*` files run Zhangjt
`/g7/anxq/Zhangjt/workspace/auto-pollen`. Do not use them for this hybrid run.

## Server Locations

Deploy these folders to the server under:

```text
/g7/anxq/Zhangjt/workspace/Smanager/auto-lijt-pollen
/g7/anxq/Zhangjt/workspace/Smanager/auto-wrfchem-pollen
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow
```

The template expects Lijt's integration source tree at:

```text
/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre3
```

The emission model data are read from:

```text
/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim
/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Plant_function_type_CLM.nc
/g7/anxq/Zhangjt/workspace/pollen_forcast/meic-2017-0p25-RADM2
```

## Split Tasks

The run is split into 20-day chunks, with the last chunk shortened:

```text
20240701 -> 20240721  20 days
20240721 -> 20240810  20 days
20240810 -> 20240830  20 days
20240830 -> 20240919  20 days
20240919 -> 20241001  12 days
```

Generated commands files:

```text
commands.lijt_hybrid_neimeng_20240701_20240721.json
commands.lijt_hybrid_neimeng_20240721_20240810.json
commands.lijt_hybrid_neimeng_20240810_20240830.json
commands.lijt_hybrid_neimeng_20240830_20240919.json
commands.lijt_hybrid_neimeng_20240919_20241001.json
```

Regenerate them after editing shared parameters:

```bash
cd /g7/anxq/Zhangjt/workspace/Smanager/auto-lijt-pollen/manual_neimeng_240701_241001
python3 generate_commands.py
```

## Key Parameters

Current template values:

```text
AREA=Neimeng
LIJT_SOURCE_ROOT=/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre3
PARAM_ROOT=/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/Autumn_phenological_model_DATA/DOY_optimal_parameters
EF_ROOT=/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/ef_DL_history/ef_surface/ef_surface_2d
EF_CHEN_ROOT=/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/ef_DL_history-Chenopods_0p3/ef_surface/ef_surface_2d
MEIC_DIR=/g7/anxq/Zhangjt/workspace/pollen_forcast/meic-2017-0p25-RADM2
POLLEN_LAT_MIN=35.0
POLLEN_LAT_MAX=50.0
POLLEN_LON_MIN=95.0
POLLEN_LON_MAX=125.0
POLLEN_GRID_RES=0.1
LIJT_TIME_STEP=180
LIJT_WRF_NTASKS=384
LIJT_WRF_NTASKS_PER_NODE=32
```

The `POLLEN_*` and `TEMPERATURE_*` bounds are the Neimeng calculation box used
by the Lijt emission model. If the exact operational Neimeng WRF domain differs,
edit these values in `generate_commands.py`, regenerate the commands files, and
rerun `preflight`.

## Plan And Submit

Run on the server:

```bash
cd /g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow
PY=/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python
CMD_DIR=../auto-lijt-pollen/manual_neimeng_240701_241001
```

Preflight one file first:

```bash
$PY flowctl.py preflight \
  --commands-file $CMD_DIR/commands.lijt_hybrid_neimeng_20240701_20240721.json
```

Plan all chunks:

```bash
$PY flowctl.py plan --run-id lijt_hybrid_neimeng_20240701_20240721 --start 2024-07-01T12:00:00 --end 2024-07-21T12:00:00 --period autumn --domain neimeng --variant lijt_hybrid --met-provider fnl_gfs --commands-file $CMD_DIR/commands.lijt_hybrid_neimeng_20240701_20240721.json
$PY flowctl.py plan --run-id lijt_hybrid_neimeng_20240721_20240810 --start 2024-07-21T12:00:00 --end 2024-08-10T12:00:00 --period autumn --domain neimeng --variant lijt_hybrid --met-provider fnl_gfs --commands-file $CMD_DIR/commands.lijt_hybrid_neimeng_20240721_20240810.json
$PY flowctl.py plan --run-id lijt_hybrid_neimeng_20240810_20240830 --start 2024-08-10T12:00:00 --end 2024-08-30T12:00:00 --period autumn --domain neimeng --variant lijt_hybrid --met-provider fnl_gfs --commands-file $CMD_DIR/commands.lijt_hybrid_neimeng_20240810_20240830.json
$PY flowctl.py plan --run-id lijt_hybrid_neimeng_20240830_20240919 --start 2024-08-30T12:00:00 --end 2024-09-19T12:00:00 --period autumn --domain neimeng --variant lijt_hybrid --met-provider fnl_gfs --commands-file $CMD_DIR/commands.lijt_hybrid_neimeng_20240830_20240919.json
$PY flowctl.py plan --run-id lijt_hybrid_neimeng_20240919_20241001 --start 2024-09-19T12:00:00 --end 2024-10-01T12:00:00 --period autumn --domain neimeng --variant lijt_hybrid --met-provider fnl_gfs --commands-file $CMD_DIR/commands.lijt_hybrid_neimeng_20240919_20241001.json
```

Submit all chunks:

```bash
$PY flowctl.py submit --run-id lijt_hybrid_neimeng_20240701_20240721
$PY flowctl.py submit --run-id lijt_hybrid_neimeng_20240721_20240810
$PY flowctl.py submit --run-id lijt_hybrid_neimeng_20240810_20240830
$PY flowctl.py submit --run-id lijt_hybrid_neimeng_20240830_20240919
$PY flowctl.py submit --run-id lijt_hybrid_neimeng_20240919_20241001
```

Or use the bundled helper:

```bash
cd /g7/anxq/Zhangjt/workspace/Smanager/auto-lijt-pollen/manual_neimeng_240701_241001
bash submit_all.sh
```

To validate without submitting:

```bash
DRY_RUN=true bash submit_all.sh
```

## Manual Node Order

Each run executes:

```text
prepare_case
wps_fnl
wps_gfs
real
generate_wrfchemi
wrf_run
postprocess
```

To run one node by hand:

```bash
$PY flowctl.py run-node --run-id lijt_hybrid_neimeng_20240701_20240721 --node prepare_case
```

## Where Files Are Created

After `prepare_case`, the run directory is:

```text
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/<run_id>
```

The copied Lijt case root is:

```text
runs/<run_id>/case/WRFChem_autumn_Beijing_pre3
```

WPS is run under:

```text
runs/<run_id>/case/WRFChem_autumn_Beijing_pre3/WRF-pollen1/WPS-master
```

WPS output is saved under:

```text
runs/<run_id>/case/WRFChem_autumn_Beijing_pre3/WPS_met_save_data/pre<days>days_12-12_2/2024/<LIJT_START_DATE>/met_em.d01.*
```

WRF/real is run under:

```text
runs/<run_id>/case/WRFChem_autumn_Beijing_pre3/WRF-pollen1/WRF-pollen_Tot_Arte_Chen/test/em_real
```

`real` outputs:

```text
wrfinput_d01
wrfbdy_d01
```

`generate_wrfchemi` outputs:

```text
runs/<run_id>/temperature/
runs/<run_id>/pollen_flux/
runs/<run_id>/wrfchemi_meic/
runs/<run_id>/wrfchemi/wrfchemi_d01_YYYY-MM-DD_12_00_00.nc
```

`wrf_run` outputs:

```text
runs/<run_id>/wrfout/wrfout_d01_*
```

No `product_extract` or `package_products` nodes are included in this template.

## Monitoring

```bash
$PY flowctl.py status --run-id lijt_hybrid_neimeng_20240701_20240721
$PY flowctl.py logs --run-id lijt_hybrid_neimeng_20240701_20240721 --node generate_wrfchemi --tail 200
$PY flowctl.py logs --run-id lijt_hybrid_neimeng_20240701_20240721 --node wrf_run --tail 200
squeue -u anxq -o '%i|%j|%T|%M|%l|%D|%R'
```
