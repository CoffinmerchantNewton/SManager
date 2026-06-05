# Production Operations Policy

本文覆盖生产运行中的安全、重试、日志、磁盘清理和备份恢复策略。默认边界是：跳板机负责控制与外网下载，内网服务器负责离线计算。

## Security

- Store `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY`, `SERVER_SSH_PASSWORD`, FNL credentials and webhook URLs only in private `.env` files.
- Do not print passwords or bearer tokens in CLI output, backend logs or Git commits.
- Rotate `SECRET_KEY` and admin password when handing over machines or after incident response.
- Management routes require bearer token. Login is intentionally single-account and suitable for a small trusted operations group, not RBAC/SSO.
- Products read APIs may stay public for the Portal, but write operations and system/run management require authentication.
- Hermes/AI operators must call `packages/cli/smanager.py`; direct SSH is reserved for manual incident recovery.

## Retry Guardrails

- Default automatic actions are limited by `AGENT_MAX_AUTO_ACTIONS_PER_RUN`.
- `AGENT_TICK_INTERVAL_MINUTES` controls watch frequency. Avoid tight polling against Slurm and SSH.
- FNL repair retries should back off after download/upload failures and always run server-side verification after upload.
- Submit defaults to `--dry-run` in runbooks. Remove dry-run only after preflight, FNL verification and commands-file review pass.
- Automatic retry is allowed for transient SSH, Slurm submission and known recoverable node errors. It is not allowed for source-code changes, destructive deletion, repeated FNL overwrite, or unbounded WRF reruns.

## Logging

Jumpbox:

- Backend logs should be retained under `runtime/logs` or the service manager journal.
- CLI output for scheduled jobs should be redirected to timestamped files if run from cron/systemd.
- Store only summaries and product indexes in SQLite; avoid inserting large binary output.

Server:

- Node logs remain with the run directory and are exposed through `flowctl logs`.
- `events.jsonl` and status JSON files are the structured audit layer.
- Slurm stdout/stderr paths should be included in node status when available.

Log rotation recommendation:

- Keep operational logs for at least `STORAGE_RETENTION_DAYS`.
- Compress or archive old successful run logs before deletion when they are needed for reproducibility.
- Never delete logs for failed or manually investigated runs until the incident note is complete.

## Storage Lifecycle

Configured variables:

- `STORAGE_RETENTION_DAYS`
- `STORAGE_MAX_GB`
- `JUMPBOX_FNL_CACHE_DIR`
- `JUMPBOX_PRODUCTS_DIR`
- `JUMPBOX_LOGS_DIR`
- `JUMPBOX_MANIFESTS_DIR`
- `JUMPBOX_CACHE_DIR`

Recommended workflow:

```bash
python packages/cli/smanager.py storage-cleanup --dry-run
python packages/cli/smanager.py storage-cleanup
```

Cleanup should:

- Ignore `.gitkeep`.
- Prefer deleting cache, temporary logs and old synced copies before product manifests.
- Never delete server-side original output from the jumpbox cleanup command.
- Keep enough recent products for Portal and historical comparison.

## Backup

Back up from the jumpbox:

- `.env` through a private secret manager or encrypted backup.
- `runtime/db/pollen_forecast.sqlite`.
- `runtime/manifests`.
- Published products under `runtime/products`.
- Operation docs and runbooks through Git.

Back up from the server:

- Commands-file used for production.
- Run specs, status JSON, event JSONL and product manifests.
- Selected successful run products.
- Server environment notes for module load, Slurm partition and executable paths.

Do not back up raw WRF/NetCDF outputs into Git. Use external archive storage when long-term retention is required.

## Restore

1. Restore repository at the target commit on the jumpbox.
2. Restore private `.env`.
3. Restore SQLite database and runtime manifests/products as needed.
4. Run backend migration startup or `python -m compileall` smoke checks.
5. Run `python packages/cli/smanager.py preflight`.
6. Verify one existing run can load status, logs and products.
7. Start backend/frontend services.

## Incident Boundary

Escalate to manual operator confirmation when:

- Preflight reports missing WPS/WRF/Slurm/template paths.
- FNL repair fails after configured retries.
- Slurm repeatedly rejects submission.
- Disk cleanup would remove more than expected or cross configured roots.
- Product manifest is missing after a successful WRF run.
