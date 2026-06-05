# Production Topology and Data Contracts

本文定义 SManager 生产部署边界、关键路径和数据契约。目标是让跳板机、内网计算服务器、CLI/Hermes、前端管理端之间只通过明确接口协作，避免把凭据、服务器路径和大文件散落在业务代码中。

## Topology

```text
operator / Hermes / cron
  -> packages/cli/smanager.py
  -> FastAPI backend on jumpbox
  -> SSH to 10.40.140.17
  -> /g7/anxq/Zhangjt/workspace/Smanager/server/auto-pollen-flow/flowctl.py
  -> Slurm + existing auto-pollen under /g7/anxq/Zhangjt/workspace/auto-pollen
  -> products/logs/manifests copied back to jumpbox runtime/
  -> React frontend reads backend API
```

## Runtime Locations

Jumpbox:

- Repository: `E:\SManager`
- Private configuration: `.env` or `backend/.env`
- Database: `runtime/db/pollen_forecast.sqlite`
- FNL cache: `runtime/fnl`
- Product archive: `runtime/products`
- Cached logs and manifests: `runtime/logs`, `runtime/manifests`

Server:

- Repository copy: `/g7/anxq/Zhangjt/workspace/Smanager`
- Existing auto-pollen: `/g7/anxq/Zhangjt/workspace/auto-pollen`
- Template root: `/g7/anxq/Zhangjt/workspace/auto-pollen/template`
- Flow package: `/g7/anxq/Zhangjt/workspace/Smanager/server/auto-pollen-flow`
- Production commands template: `server/auto-pollen-flow/templates/run_spec/commands.auto_pollen.production.json`
- Run state, logs, products: under the configured server flow root.

Secrets stay only in private configuration. Do not commit SSH passwords, FNL download credentials, webhook URLs, or long-lived tokens.

## Control Interfaces

Backend public/admin API:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/system/preflight`
- `POST /api/v1/system/storage/cleanup`
- Existing run, FNL, product, scheduler, dashboard and agent routes.

CLI:

- `login`
- `preflight`
- `config-template`
- `storage-cleanup --dry-run`
- `runs-batch`
- `products-batch`
- Existing `runs/status/fnl-verify/fnl-repair/submit/logs/events/diagnose/collect-context/retry/cancel/sync-products` commands.

Server flow:

- `flowctl plan`
- `flowctl preflight`
- `flowctl fnl-verify`
- `flowctl submit --dry-run`
- `flowctl status --json`
- `flowctl logs`
- `flowctl diagnose`
- `flowctl products`

## Data Contracts

Run spec:

- Source of truth for forecast window, period, domain, variant, FNL requirements, node graph and command environment.
- Created by `flowctl plan` or backend run creation.
- Must be readable by backend and CLI without parsing logs.

FNL manifest:

- Records each required valid time, filename, status, source, size, path and verification result.
- Valid server files are preferred. Download and upload happen only for missing or invalid entries.
- Upload is followed by server-side verification before submit.

Workflow status:

- `workflow.status.json` summarizes overall state and progress.
- `state/<node>.status.json` records each node state, attempt, log paths, error code and Slurm job id.
- Backend persists snapshots into SQLite for frontend and audit views.

Product manifest:

- `products/product_manifest.json` is the canonical product index on the server.
- Each entry should include `type`, `subtype`, `variable`, `unit`, `bounds`, `lead_time`, `source_run_id`, `path` and optional `capability_status`.
- Frontend must discover renderable layers from manifest/product API instead of hard-coding server paths.

Agent action audit:

- Every automatic or operator-triggered recovery action records action type, reason, input state, command, output, success flag and timestamp.
- Hermes/AI should use CLI/API only; it should not SSH directly into the server for normal operations.

## Remaining External Calibration

The repository now contains production wiring, preflight checks, auth, storage lifecycle, product metadata and Portal controls. Two things are intentionally configuration/business tasks:

- Real business risk thresholds must be calibrated with domain owners.
- A full small-window forecast must be executed on the CentOS server after private credentials and production commands are confirmed.
