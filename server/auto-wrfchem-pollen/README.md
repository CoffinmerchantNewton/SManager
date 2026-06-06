# WRFChem Pollen Takeover Flow

This package contains the isolated WRFChem autumn Beijing pollen workflow used
with `server/auto-pollen-flow/flowctl.py`.

The workflow is intentionally separate from the legacy `auto-pollen` runtime.
It builds the WPS/WRF case in the run directory, generates temperature inputs,
pollen emissions, MEIC WRFChem emissions, and final `wrfchemi` files from raw
or public inputs. It must not depend on previously generated pollen flux,
`pre7days`, or `wrfchemi` products.

## Current Milestone Run

- Run ID: `20250815_autumn_beijing_wrfchem_takeover`
- Forecast start: `2025-08-15 12:00`
- Forecast length: 7 days
- Remote Smanager root: `/g7/anxq/Zhangjt/workspace/Smanager`
- Remote flow package: `/g7/anxq/Zhangjt/workspace/Smanager/auto-wrfchem-pollen`
- Commands file: `commands.wrfchem_pollen_20250815.json`

## Runtime Environment

Python nodes source `/g7/anxq/Zhangjt/workspace/load_env.sh`, which activates
the `wrfTool` conda environment. WPS and WRF executable nodes still load the
2017 Intel/MPI/NetCDF module stack used by the reference Beijing WRFChem
binaries.

The Smanager control nodes use the `serial` Slurm partition. The inner WRFChem
model run keeps the reference 576-task `normal` partition submission.

## Deploy

From the repository root:

```bash
bash server/deploy/sync_wrfchem_pollen.sh anxq@10.40.140.17 \
  /g7/anxq/Zhangjt/workspace/Smanager/auto-wrfchem-pollen
```

Then on the server:

```bash
cd /g7/anxq/Zhangjt/workspace/Smanager
source /g7/anxq/Zhangjt/workspace/load_env.sh
python auto-pollen-flow/flowctl.py preflight \
  --commands-file auto-wrfchem-pollen/commands.wrfchem_pollen_20250815.json
python auto-pollen-flow/flowctl.py plan \
  --run-id 20250815_autumn_beijing_wrfchem_takeover \
  --start 2025081312 --end 2025082212 \
  --period autumn --domain beijing --variant wrfchem_takeover \
  --commands-file auto-wrfchem-pollen/commands.wrfchem_pollen_20250815.json
python auto-pollen-flow/flowctl.py submit \
  --run-id 20250815_autumn_beijing_wrfchem_takeover
```
