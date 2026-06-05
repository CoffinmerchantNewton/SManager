# Production Validation Runbook

本文用于在真实服务器上做只读预检、dry-run 和小窗口实跑验证。除最后的小窗口实跑外，命令不应启动真实大任务。

## Preconditions

- Jumpbox private `.env` contains server host, user and either key settings or `SERVER_SSH_PASSWORD`.
- `ADMIN_USERNAME`, `ADMIN_PASSWORD` and `SECRET_KEY` are configured.
- `SERVER_FLOWCTL_PATH` points to the server flowctl path.
- `SERVER_FLOW_ROOT`, `SERVER_FNL_ROOTS` and `SERVER_FNL_UPLOAD_DIR` point to server-side production directories.
- `FNL_DOWNLOAD_COMMAND` is configured only when testing repair.
- Production commands-file has been reviewed.

## Login

```bash
python packages/cli/smanager.py login --username "$ADMIN_USERNAME"
```

The CLI stores the bearer token locally. Scheduled jobs may also use `SMANAGER_TOKEN`.

## Jumpbox Preflight

```bash
python packages/cli/smanager.py doctor
python packages/cli/smanager.py preflight
python packages/cli/smanager.py config-template
```

Expected result:

- Backend can load configuration.
- SSH/local flow mode is reachable.
- `flowctl`, Python, bash, Slurm, WPS/WRF executables, template directory, FNL roots, product directory and log directory are reported.
- Failures are explicit enough to fix private configuration without reading backend code.

## Server Read-only Preflight

Run through backend/CLI:

```bash
python packages/cli/smanager.py preflight --json
```

Or manually on the server when an operator is already logged in:

```bash
cd /g7/anxq/Zhangjt/workspace/Smanager/server/auto-pollen-flow
python3 flowctl.py preflight \
  --commands-file templates/run_spec/commands.auto_pollen.production.json \
  --json
```

Do not continue until every required path and command is either `ok` or explicitly marked optional.

## Plan and FNL Verify

```bash
python packages/cli/smanager.py plan \
  --start 2026060400 \
  --end 2026060500 \
  --period spring \
  --domain neimeng \
  --variant official

python packages/cli/smanager.py fnl-verify --run-id <run_id>
```

If FNL entries are missing or invalid, run repair in dry-run or controlled mode:

```bash
python packages/cli/smanager.py fnl-repair --run-id <run_id> --dry-run
```

Only run real repair after confirming `FNL_DOWNLOAD_COMMAND` and upload destination.

## Submit Dry-run

```bash
python packages/cli/smanager.py submit --run-id <run_id> --dry-run
python packages/cli/smanager.py status --run-id <run_id>
python packages/cli/smanager.py events --run-id <run_id> --limit 100
```

Expected result:

- Slurm command is rendered but no large WRF job is started.
- Node order, resource settings and log paths are visible.
- Dry-run status/event records are written.

## Product Sync Smoke

If sample products or previous products exist:

```bash
python packages/cli/smanager.py sync-products --run-id <run_id>
python packages/cli/smanager.py products --run-id <run_id>
python packages/cli/smanager.py products-batch --limit 20
```

Portal should be able to render `city_forecast_json`, PNG overlay metadata and any GeoJSON layers listed in the manifest.

## Small-window Real Run

Only after preflight, FNL verify and submit dry-run pass:

```bash
python packages/cli/smanager.py submit --run-id <run_id>
python packages/cli/smanager.py status --run-id <run_id>
python packages/cli/smanager.py diagnose --run-id <run_id> --summary
```

Monitor until completion:

```bash
python packages/cli/smanager.py events --run-id <run_id> --limit 200
python packages/cli/smanager.py logs --run-id <run_id> --node wrf_run --tail 80
python packages/cli/smanager.py sync-products --run-id <run_id>
```

Record:

- Exact run id and commit hash.
- Commands-file checksum.
- FNL manifest summary.
- Slurm job ids.
- Runtime duration per major node.
- Product manifest counts and capability fallback statuses.
- Portal screenshot or operator note.

## Pass Criteria

- Preflight passes or has only documented optional warnings.
- FNL manifest has no missing or invalid required files before submit.
- Dry-run does not launch large jobs.
- Small-window run completes WPS, real, WRF, postprocess and package nodes.
- Product manifest includes source run, variable, unit, subtype and bounds where applicable.
- Frontend login, Dashboard, Run Detail, Products and Portal can read the resulting run.

## Known Non-blocking Follow-ups

- Business risk thresholds still require domain calibration.
- GeoTIFF generation may report a skipped capability when scientific/GDAL dependencies are absent.
- Full operational confidence requires at least one complete production-window forecast after the small-window run.
