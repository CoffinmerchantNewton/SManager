# Overall Requirements

本文整理 SManager 后续要建设的整体需求。所有实现默认在 `dev` 分支推进。

## 目标

建设一套基于 WRF-Pollen 的每日自动花粉预报系统，实现：

- 每日定时创建预报任务。
- 优先使用服务器已有 FNL；若缺失或损坏，再由跳板机下载并上传。
- 自动运行 WPS、real、WRF-Pollen、后处理和产品打包。
- 通过后端 API 和前端展示任务进度、日志、诊断和历史产物。
- Hermes-agent 自动值守、有限重试、异常通知。
- AI 助手可以通过 CLI 读取状态、辅助诊断、执行受控恢复动作。

## 部署边界

### 内网服务器

服务器不能联网，只负责离线计算和状态落盘。

放置内容：

- `server/auto-pollen-flow/`：服务器 flow 包装层，提供 `flowctl`。
- 现有 `wrf-pollen/auto-pollen/`：WPS/WRF 自动化脚本，先由 `flowctl` 包装。
- WRF-Pollen 源码或已编译可执行文件。
- WPS/WRF 模板、环境脚本、conda 环境、Slurm 作业脚本。
- WPS geog、树木/草地 TIF、必要观测文件。
- 服务器本地 FNL 主目录和备用目录。
- `runs/`、`WPS/`、`WRF/`、`logs/`、`products/` 等运行态目录。

不放置内容：

- 前端服务。
- 跳板机后端主服务。
- Hermes-agent 主循环。
- 跳板机 SQLite 主库。
- 外网下载逻辑。

### 跳板机

跳板机可以联网，也可以 SSH 到服务器。

放置内容：

- `apps/backend/`：FastAPI 后端。
- `apps/frontend/`：React 前端。
- `apps/hermes-agent/`：自动值守器。
- `packages/`：共享契约、诊断规则、CLI。
- `runtime/`：SQLite、FNL 下载缓存、产物归档、manifest、日志缓存。

## 每日主流程

```text
schedule_daily_run
  -> create_run_spec
  -> server_fnl_scan
  -> if fnl_ok:
       submit_server_flow
     else:
       download_missing_or_bad_fnl_on_jumpbox
       verify_downloaded_fnl
       upload_fnl_to_server
       server_fnl_scan_again
       submit_server_flow
  -> monitor_slurm_and_status_files
  -> diagnose_error_if_any
  -> retry_by_policy_or_notify
  -> sync_products_to_jumpbox
  -> index_products_in_db
  -> frontend_display
```

## FNL 需求

服务器上通常会有 FNL，但可能存在以下问题：

- 某些时次缺失。
- 文件截断或过小。
- 文件内容不是 GRIB，例如错误页占位。
- 软链接失效。
- 主目录文件损坏，但备用目录有好副本。

因此 FNL 保障必须按以下顺序：

1. 计算本次 run 需要的所有 FNL 时次。
2. SSH 到服务器执行 `flowctl fnl-verify` 或包装后的 `copy_fnl.py --scan-only`。
3. 服务器扫描主目录和备用目录，优先选择已有有效副本。
4. 若服务器已有有效副本，则不下载、不上传。
5. 若有缺失或损坏，后端/Hermes-agent 只下载这些问题时次。
6. 跳板机本地校验下载文件。
7. 上传到服务器目标目录或 staging 目录。
8. 服务器再次校验。
9. 校验通过后才能提交 WPS/WRF。

FNL 状态至少包括：

- `valid_time`
- `file_name`
- `status`: `server_ok`、`missing`、`bad_magic`、`too_small`、`link_broken`、`downloaded`、`uploaded`、`verified`
- `source`: `server_primary`、`server_fallback`、`jumpbox_download`
- `server_path`
- `local_path`
- `size_bytes`
- `valid_grib`
- `checked_at`

## 服务器 Flow 需求

服务器侧必须提供统一 CLI：

```bash
flowctl plan
flowctl fnl-verify
flowctl submit
flowctl status --json
flowctl logs
flowctl diagnose
flowctl retry
flowctl products
```

服务器 flow 必须写：

- `run_spec.json`
- `state/workflow.status.json`
- `state/<node>.status.json`
- `events.jsonl`
- `fnl_manifest.json`
- `products/product_manifest.json`

状态文件是后端和 Hermes-agent 的主数据源，日志只用于诊断。

## 后端需求

后端负责：

- 管理 run、node、event、FNL、product 元数据。
- 通过 SSH 调用服务器 `flowctl`。
- 管理跳板机 FNL 下载缓存和上传。
- 同步服务器状态到 SQLite。
- 给前端提供 API。
- 给 Hermes-agent 提供可复用 service。

核心 API：

```text
POST /api/v1/runs
POST /api/v1/runs/{run_id}/submit
GET  /api/v1/runs/{run_id}/status
GET  /api/v1/runs/{run_id}/logs
POST /api/v1/runs/{run_id}/retry

GET  /api/v1/fnl/coverage
POST /api/v1/fnl/verify-server
POST /api/v1/fnl/download-missing
POST /api/v1/fnl/upload

GET  /api/v1/products
GET  /api/v1/products/{product_id}
```

## Hermes-agent 需求

Hermes-agent 负责自动值守：

- 定时创建每日 run。
- 先做服务器 FNL 扫描。
- 仅在 FNL 缺失或损坏时触发下载上传。
- 轮询服务器状态和 Slurm 状态。
- 对常见错误执行有限重试。
- 同步成功产物。
- 发送通知。

自动动作必须记录审计：

- 动作类型。
- 触发原因。
- 输入状态。
- 执行命令。
- 输出结果。
- 是否成功。

## 前端需求

前端优先支持：

- Dashboard：今日运行、FNL 覆盖、Slurm 状态、最新告警。
- Run Detail：DAG、节点状态、日志、诊断、重试入口。
- FNL Management：按时次查看服务器已有、缺失、损坏、已补齐。
- Products：历史预报产物、地图、站点时间序列、CSV/PNG/GeoJSON 下载。
- Scheduler：每日任务配置。

## AI 辅助边界

AI 助手不能直接做不可逆操作。

允许动作：

- 读取 `flowctl status/logs/diagnose`。
- 读取后端状态和数据库摘要。
- 建议错误原因。
- 调用受控 retry。
- 触发 FNL 补齐。

不允许自动动作：

- 删除整个 run 目录。
- 覆盖已验证成功的 FNL。
- 修改 WRF 源码后直接生产运行。
- 无限重试。

## MVP 验收

第一版 MVP 至少满足：

1. 后端可以创建 run。
2. 后端可以 SSH 调服务器做 FNL 扫描。
3. 服务器 FNL 完整时，不触发下载上传。
4. 服务器 FNL 缺失或损坏时，只补齐问题时次。
5. 服务器可以提交现有 `auto_wrf.py` 包装流程。
6. 后端可以读取结构化状态。
7. 前端可以展示 run 状态。
8. Hermes-agent 可以完成一次只读巡检和通知。
