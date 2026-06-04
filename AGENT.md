# China Pollen Forecast System 工程实施规划

本文面向后续开发者和 AI 助手，描述如何把当前 `auto-pollen` 脚本体系升级为一套可每日自动运行、可观测、可恢复、可由 AI 辅助诊断和重试的花粉预报业务系统。

## 背景

项目目标是基于 WRF-Pollen / WRF-Chem 建设全国或区域花粉扩散业务预报平台。

当前运行环境分为两台机器：

- 内网 CentOS 服务器：不能访问外网，负责 WPS、WRF、WRF-Pollen、后处理等重计算任务，可使用 Slurm 队列。
- 跳板机笔记本：可以访问外网，也可以 SSH 登录内网服务器，负责下载 FNL、上传输入数据、轮询任务状态、下载产物、提供后端 API、运行前端，并为 Hermes/AI 助手提供 CLI 控制面。

当前 `wrf-pollen/auto-pollen/` 已经能做单次或批量运行：

- `auto_wrf.py`：单个时段的 WPS -> real -> pollen prep -> sbatch 提交流程。
- `batch_run.sh`：批量提交多个季节窗口，prep 成功后提交 WRF，并可自动 eval。
- `scripts/copy_fnl.py`：在服务器本地 FNL 主备目录中扫描、校验、复制或软链接 FNL。
- `batch_eval_pollen.sh`：批量评估已有 WRF 输出。
- `restart_all_runs.sh`：按 restart 文件续跑历史任务。

当前 `backend/` 已接入服务器 `flowctl` 控制面、FNL 补齐、产物同步、运行事件和本地 storage 快照；`frontend/` 已有运行控制、FNL 管理、产物列表下载和主题切换。仍未完成的是把真实 WPS/WRF 节点命令、`product_extract` 产物提取、非空 `product_manifest` 和真实花粉分布地图渲染完整串起来。

## 总体原则

1. 服务器只做可离线执行的计算 flow，不依赖外网。
2. 跳板机负责联网、跨机器同步、调度入口、状态聚合、通知和 AI 决策。
3. 所有节点必须幂等：重复执行同一节点不会破坏已有成功产物。
4. 所有关键状态必须结构化落盘，不能只靠日志文本。
5. AI 自动重试必须受规则约束：先确定性诊断，再选择有限动作，超过次数通知人工。
6. 后端、Hermes/AI 助手尽量复用同一套 CLI，避免各自绕过业务逻辑。
7. 大文件不进数据库，数据库只保存元数据、索引、状态和路径。
8. 每次优化都要以可维护性为前提：测试通过后直接修改到最有用的实现，不以补丁堆叠方式保留新旧两套实现。

## 目标目录架构

项目目录按职责拆成五层：

1. `apps/`：跳板机上运行的用户界面和后端服务；不再维护独立 `apps/hermes-agent`。
2. `packages/`：前后端和 agent 共用的契约、类型、CLI、诊断规则。
3. `server/`：要部署到内网服务器的离线 flow 包装层。
4. `runtime/`：跳板机本地运行时数据，不进 Git。
5. `wrf-pollen/`：WRF-Pollen 模式源码和现有 `auto-pollen`，先保留原状，逐步由 `server/flow` 包装。

目标结构：

```text
SManager/
  AGENT.md
  README.md
  docs/
    architecture/
      overall_requirements.md
      project_structure.md
      deployment_topology.md
      data_contracts.md
      retry_policy.md
    operations/
      daily_runbook.md
      fnl_runbook.md
      incident_playbook.md

  apps/
    backend/
      app/
        api/
          routes/
            runs.py
            fnl.py
            products.py
            diagnostics.py
            dashboard.py
        core/
          config.py
          database.py
          security.py
        models/
        schemas/
        services/
          ssh/
          flow/
          fnl/
          products/
          diagnostics/
          notifications/
        workers/
          scheduler.py
          product_sync.py
      tests/
      pyproject.toml

    frontend/
      src/
        app/
        pages/
          Dashboard/
          Runs/
          RunDetail/
          FnlManagement/
          Products/
          Scheduler/
        components/
        services/
        types/
      tests/
      package.json

  skills/
    smanager-hermes-cli/
      SKILL.md

  packages/
    contracts/
      run_spec.schema.json
      node_status.schema.json
      workflow_status.schema.json
      fnl_manifest.schema.json
      product_manifest.schema.json
    cli/
      smanager.py
    diagnostics/
      error_patterns.yaml
      recovery_actions.yaml
    python/
      smanager_common/
        models.py
        time.py
        jsonio.py
        paths.py

  server/
    auto-pollen-flow/
      flowctl.py
      nodes/
        fnl_verify.py
        wps_geogrid.py
        wps_ungrib.py
        wps_metgrid.py
        wrf_setup.py
        real.py
        compute_gdd.py
        prep_pollen.py
        wrf_run.py
        postprocess_eval.py
        product_extract.py
        package_products.py
      lib/
        config.py
        state.py
        events.py
        slurm.py
        paths.py
        lock.py
        diagnostics.py
      templates/
        sbatch/
        run_spec/
      tests/
    deploy/
      install_server_flow.sh
      sync_to_server.sh

  runtime/
    db/
      pollen_forecast.sqlite
    fnl/
    products/
    logs/
    manifests/
    cache/

  wrf-pollen/
    auto-pollen/
    run/
    chem/
    Registry/
```

### 当前到目标的迁移

不要一次性移动所有代码。先新建目标目录，再逐步搬迁和补兼容入口。

| 当前目录 | 目标目录 | 策略 |
| --- | --- | --- |
| `backend/` | `apps/backend/` | 第二阶段迁移，先保持原路径可运行；迁移时保留旧入口或更新 README |
| `frontend/` | `apps/frontend/` | 等真实 API 稳定后迁移，避免 UI 开发被路径调整打断 |
| `wrf-pollen/auto-pollen/` | `server/auto-pollen-flow/` 包装它 | 不直接搬 WRF 脚本，先做 wrapper 和状态协议 |
| 根目录 `AGENT.md` | 保持根目录 | 作为 AI 助手和工程协作入口 |
| 运行产物 | `runtime/` | 不进 Git，后端只保存索引和 manifest |

第一阶段建议只新增：

```text
docs/architecture/
packages/contracts/
packages/diagnostics/
server/auto-pollen-flow/
runtime/.gitkeep
```

### 目录边界

`apps/backend/`：

- FastAPI 服务。
- 只通过 SSH/CLI 操作服务器，不直接假设服务器文件可本地访问。
- 负责数据库、API、认证、通知、产物索引。

`apps/frontend/`：

- 只调用后端 API。
- 不存业务规则，不直接拼服务器路径。
- 页面围绕 `run_id`、DAG 节点、FNL 覆盖、产物浏览展开。

`skills/smanager-hermes-cli/`：

- Hermes/AI 助手的操作说明入口。
- 只通过 `packages/cli/smanager.py` 调用后端 API，不直接 SSH 到服务器。
- 当需要扩展自动值守能力时，优先扩展后端 API 和 CLI 契约，不恢复第二套 agent 代码。

`packages/contracts/`：

- 放 JSON Schema 或 Pydantic 可导出的契约。
- 服务器 flow、后端、CLI、前端类型都从这里对齐。
- 状态文件字段变化必须先改 contracts。

`packages/diagnostics/`：

- 放错误模式和恢复动作。
- AI 助手、Hermes、后端诊断接口共用。

`server/auto-pollen-flow/`：

- 只包含可部署到内网服务器的轻量 Python/SH 包装层。
- 不依赖跳板机数据库，不依赖外网。
- 通过 `flowctl.py` 暴露稳定 CLI。

`runtime/`：

- 跳板机本地运行态数据。
- 必须加入 `.gitignore`。
- 只保留 `.gitkeep` 之类占位文件。

`wrf-pollen/`：

- 模式源码和已有自动化脚本。
- 继续作为计算核心和历史研发记录所在地。
- `server/auto-pollen-flow` 成熟前，不大规模重排该目录。

### 包命名建议

Python 包：

- 后端公共包：`smanager_common`
- 服务器 flow：`auto_pollen_flow`
- Hermes/AI skill：`smanager-hermes-cli`

CLI：

- 跳板机统一 CLI：`smanager`
- 服务器统一 CLI：`flowctl`

### Git 忽略建议

后续应在 `.gitignore` 中加入：

```text
runtime/db/*.sqlite
runtime/fnl/**
runtime/products/**
runtime/logs/**
runtime/manifests/**
runtime/cache/**
wrf-pollen/auto-pollen/runs/**
wrf-pollen/auto-pollen/WPS/**
wrf-pollen/auto-pollen/WRF/**
wrf-pollen/auto-pollen/logs/**
```

保留必要占位：

```text
!runtime/.gitkeep
!runtime/db/.gitkeep
!runtime/fnl/.gitkeep
!runtime/products/.gitkeep
!runtime/logs/.gitkeep
!runtime/manifests/.gitkeep
!runtime/cache/.gitkeep
```

`auto-pollen` 现有脚本不要一次性推翻，第一阶段以包装和补状态为主。

## 运行 ID

所有系统对象都应围绕 `run_id`。

建议格式：

```text
YYYYMMDDHH_<period>_<domain>_<variant>
```

示例：

```text
2026060400_spring_neimeng_official
2026080100_autumn_neimeng_gdd805
```

每次运行必须保存：

- `run_id`
- 起止时间：`start`, `end`
- 季节：`spring/summer/autumn`
- 区域和域配置
- 驱动数据源：`FNL`、后续可扩展 `GFS/GDAS`
- 代码版本：WRF-Pollen commit、auto-pollen commit
- 编译版本或可执行文件路径
- namelist 快照
- FNL manifest
- Slurm job id
- retry attempt
- 产物路径和 checksum

## 服务器 Flow DAG

标准每日或业务运行 DAG：

```text
run_plan
  -> fnl_verify
  -> wps_geogrid
  -> wps_ungrib
  -> wps_metgrid
  -> wrf_setup
  -> real
  -> compute_gdd
  -> prep_pollen
  -> wrf_run
  -> postprocess_eval
  -> product_extract
  -> package_products
```

说明：

- `run_plan`：生成 `run_spec.json`，锁定本次参数。
- `fnl_verify`：校验服务器上 FNL 是否齐全、大小是否合理、magic 是否为 GRIB。
- `wps_geogrid`：可按区域和网格复用，不必每次重跑。
- `wps_ungrib`：依赖 FNL。
- `wps_metgrid`：依赖 geogrid 和 ungrib。
- `wrf_setup`：复制或链接 WRF 模板、生成 `namelist.input`、链接 `met_em`。
- `real`：生成 `wrfinput_d0X` 和 `wrfbdy_d01`。
- `compute_gdd`：计算初始 GDD。
- `prep_pollen`：注入 `FRAC_POLLEN_*`、`POLLEN_GDD_*`、`NTOTAL_POLLEN_*`。
- `wrf_run`：提交或运行 `wrf.exe`。
- `postprocess_eval`：沉降评估、站点匹配、时间序列分析。
- `product_extract`：提取前端可展示的数据产品。
- `package_products`：生成产物 manifest，供跳板机下载和索引。

## 状态文件协议

每个节点写一个状态文件：

```text
runs/<run_id>/state/<node>.status.json
```

工作流汇总状态：

```text
runs/<run_id>/state/workflow.status.json
```

事件流：

```text
runs/<run_id>/events.jsonl
```

节点状态示例：

```json
{
  "run_id": "2026060400_spring_neimeng_official",
  "node": "wps_ungrib",
  "status": "running",
  "progress": 35,
  "attempt": 1,
  "slurm_job_id": "123456",
  "started_at": "2026-06-04T08:00:00+08:00",
  "updated_at": "2026-06-04T08:12:00+08:00",
  "finished_at": null,
  "error_code": null,
  "message": "ungrib.exe running",
  "inputs": [
    "runs/2026060400_spring_neimeng_official/fnl_manifest.json"
  ],
  "outputs": [],
  "log_files": [
    "logs/wps_ungrib.log"
  ]
}
```

`status` 枚举：

- `pending`
- `ready`
- `running`
- `success`
- `error`
- `skipped`
- `retrying`
- `cancelled`

写文件必须使用原子写：

```text
write <file>.tmp -> fsync -> mv <file>.tmp <file>
```

这样后端和 Hermes/AI 助手读取时不会遇到半截 JSON。

## 服务器 CLI

建议实现 `flowctl.py`，作为服务器侧唯一入口。

基础命令：

```bash
python flow/flowctl.py plan --run-id 2026060400_spring_neimeng_official --start 2026060400 --end 2026060700 --period spring
python flow/flowctl.py submit --run-id 2026060400_spring_neimeng_official
python flow/flowctl.py status --run-id 2026060400_spring_neimeng_official --json
python flow/flowctl.py logs --run-id 2026060400_spring_neimeng_official --node wrf_run --tail 200
python flow/flowctl.py diagnose --run-id 2026060400_spring_neimeng_official --json
python flow/flowctl.py retry --run-id 2026060400_spring_neimeng_official --node wrf_run
python flow/flowctl.py cancel --run-id 2026060400_spring_neimeng_official
python flow/flowctl.py products --run-id 2026060400_spring_neimeng_official --manifest
```

第一阶段可以让 `flowctl submit` 包装现有 `auto_wrf.py --prep-only` 和 WRF sbatch 脚本；后续再拆成真正节点级 DAG。

## Slurm 调度策略

两种实现方式都可行。

优先方案：节点脚本 + Slurm dependency。

```bash
prep_job=$(sbatch --parsable prep.sh)
wrf_job=$(sbatch --parsable --dependency=afterok:${prep_job} wrf.sh)
post_job=$(sbatch --parsable --dependency=afterok:${wrf_job} postprocess.sh)
```

优点是依赖关系交给 Slurm，缺点是状态聚合需要额外查询。

备选方案：flow driver 轮询节点。

优点是状态可控，适合复杂 AI 诊断；缺点是 driver 进程要保持运行或被定时唤醒。

建议：

- MVP 先沿用现有 `batch_run.sh` 的“prep 后提交 WRF”逻辑，但补结构化状态。
- 第二阶段改为 `sbatch --dependency=afterok`，并记录所有 job id。
- 外部 Hermes/AI 值守流程负责定时 `squeue/sacct` 和状态文件对账；本仓库通过后端 API 和 CLI 暴露查询入口。

## FNL 闭环

服务器上通常会有 FNL 数据，但有概率缺失、截断、大小异常或被错误页占位污染。因此生产流程必须是“服务器优先，本地校验通过则直接使用；只有缺失或损坏时，才由跳板机下载并上传”。

FNL 保障流程：

```text
determine_needed_fnl
  -> server_fnl_scan
  -> server_pick_best_existing_copy
  -> if server_ok: use_server_fnl
  -> if missing_or_bad:
       download_missing_fnl_to_jumpbox
       local_grib_magic_check
       write_or_update_fnl_manifest
       rsync/scp_to_server
       server_fnl_verify_again
  -> record_manifest_in_db
```

`server_fnl_scan` 应复用或包装当前 `scripts/copy_fnl.py --scan-only` 的能力，检查：

- 目标时段内每 6 小时 FNL 是否齐全。
- 文件是否大于最低阈值。
- 文件 magic 是否为 `GRIB`。
- 主目录和备用目录多副本中是否可选出体积最大的有效副本。

只有以下情况才触发跳板机下载和上传：

- 服务器主备目录都没有某个时次。
- 服务器已有文件过小或 magic 不是 `GRIB`。
- 服务器已有软链接指向失效路径。
- `ungrib.exe` 后续证明某个文件虽然通过基础校验但实际不可用。

FNL manifest 示例：

```json
{
  "provider": "FNL",
  "start": "2026060400",
  "end": "2026060700",
  "files": [
    {
      "name": "fnl_20260604_00_00.grib2",
      "size_bytes": 32768000,
      "sha256": "optional",
      "local_path": "storage/fnl/2026/20260604/fnl_20260604_00_00.grib2",
      "server_path": "/g7/anxq/Zhangjt/static/fnl/2026/20260604/fnl_20260604_00_00.grib2",
      "valid_grib": true
    }
  ]
}
```

注意：

- 文件很大时 sha256 可做可选项，至少保存 size、mtime、GRIB magic。
- manifest 需要记录文件来源：`server_existing`、`jumpbox_downloaded`、`jumpbox_uploaded`。
- 下载任务应只下载缺失或损坏时次，不重复下载服务器已验证通过的文件。
- 上传使用 `rsync --partial --inplace` 或可恢复策略。
- 上传后必须在服务器上二次运行 `copy_fnl.py --scan-only` 或新的 `flowctl fnl-verify`。
- 后续若业务要“未来预报”，FNL 可能有时效滞后，应抽象 `met_provider`，为 GFS/GDAS 预留接口。

## 跳板机后端

后端职责：

- 保存运行元数据、任务状态、日志索引、产物索引。
- 通过 SSH 调用服务器 CLI。
- 管理 FNL 下载、校验、上传。
- 提供前端 API。
- 给 Hermes/AI 助手暴露可执行动作。

建议新增服务层：

```text
backend/app/services/
  ssh_client.py       # SSH 命令执行、scp/rsync 封装
  server_flow.py      # submit/status/retry/logs/products
  fnl_store.py        # 下载、校验、manifest、上传
  product_store.py    # 产物下载、索引、本地文件服务
  storage.py          # 跳板机 runtime 本地目录快照
  diagnostics.py      # 错误分类与建议动作
```

建议新增 API：

```text
GET    /api/v1/runs
POST   /api/v1/runs
GET    /api/v1/runs/{run_id}
POST   /api/v1/runs/{run_id}/submit
GET    /api/v1/runs/{run_id}/status
GET    /api/v1/runs/{run_id}/nodes
GET    /api/v1/runs/{run_id}/logs
GET    /api/v1/runs/{run_id}/events
POST   /api/v1/runs/{run_id}/retry
POST   /api/v1/runs/{run_id}/cancel
POST   /api/v1/runs/{run_id}/sync-products

GET    /api/v1/fnl/coverage
POST   /api/v1/fnl/repair
POST   /api/v1/fnl/verify-server
POST   /api/v1/fnl/download
POST   /api/v1/fnl/upload
POST   /api/v1/fnl/verify

GET    /api/v1/products
GET    /api/v1/products/{product_id}
GET    /api/v1/products/{product_id}/download

GET    /api/v1/system/doctor
GET    /api/v1/system/storage

GET    /api/v1/diagnostics/{run_id}
POST   /api/v1/diagnostics/{run_id}/apply
```

## 轻量数据库设计

SQLite 足够作为第一阶段数据库。

建议核心表：

```text
runs
  id
  run_id
  start_time
  end_time
  period
  domain
  variant
  met_provider
  status
  progress
  attempt
  server_run_dir
  created_at
  updated_at

run_nodes
  id
  run_id
  node_name
  status
  progress
  attempt
  slurm_job_id
  started_at
  finished_at
  error_code
  message

run_events
  id
  run_id
  node_name
  level
  event_type
  message
  payload_json
  created_at

fnl_files
  id
  provider
  valid_time
  file_name
  local_path
  server_path
  size_bytes
  sha256
  valid_grib
  uploaded
  created_at

products
  id
  run_id
  product_type
  product_name
  local_path
  server_path
  mime_type
  size_bytes
  checksum
  valid_time
  published
  created_at

agent_actions
  id
  run_id
  action_type
  reason
  status
  attempt
  input_json
  output_json
  created_at
```

文件存储目录：

```text
storage/
  fnl/<year>/<yyyymmdd>/
  products/<run_id>/
  logs/<run_id>/
  manifests/<run_id>/
```

数据库只存路径和元数据，不直接存大文件。

## Hermes/AI CLI 自动值守

本仓库不再维护独立 `apps/hermes-agent` 代码。Hermes 或 AI 助手应通过 `skills/smanager-hermes-cli/SKILL.md` 学习操作方式，并通过 `packages/cli/smanager.py` 调用后端 API。需要定时触发时，由外部 Hermes、cron 或 systemd timer 调用 CLI/API；业务逻辑仍收敛在后端和服务器 `flowctl`。

职责：

- 定时检查当天/未来任务是否已创建。
- 先检查服务器 FNL 是否齐全和可用；只有缺失或损坏时才下载和上传。
- 触发服务器 flow。
- 轮询状态、Slurm 队列和日志。
- 判断是否需要自动重试。
- 下载产物并更新数据库。
- 发送机器人通知；第一版可先只写 `agent_actions` 审计和系统日志。

建议循环：

```text
external_tick_or_cli
  -> load_active_runs
  -> ensure_daily_run_created
  -> ensure_fnl_ready
  -> ensure_server_flow_submitted
  -> poll_server_status
  -> diagnose_errors
  -> apply_retry_policy
  -> sync_products_if_success
  -> notify_if_needed
```

自动重试策略：

| 错误类型 | 识别方式 | 自动动作 |
| --- | --- | --- |
| 缺 FNL | `MISSING fnl_*`、`fnl_verify error` | 先确认服务器主备目录无有效副本，再由跳板机下载并上传 |
| FNL 非 GRIB | magic 校验失败、ungrib 报 grib edition 异常 | 标记服务器副本损坏，跳板机重新下载该时次并上传 |
| ungrib 失败 | WPS 日志错误 | 重新 link FNL 后重跑 ungrib |
| metgrid 失败 | 缺 `met_em` 或 geogrid/metgrid 日志报错 | 从 WPS 相关节点重试 |
| real 层数错误 | `num_metgrid_levels`、2019-06-12 层数切换 | 拆分时段或修正 namelist |
| WRF 积分崩溃 | CFL、segfault、rsl.error | 优先 restart 续跑，必要时降 `time_step` |
| 队列提交失败 | sbatch 返回非 job id | 延迟重试提交 |
| 磁盘不足 | `No space left` | 停止自动重试并通知 |
| 产物缺失 | WRF 成功但无目标产品 | 重跑 postprocess，不重跑 WRF |

自动重试限制：

- 单节点默认最多 2 次。
- WRF restart 续跑最多 2 次。
- 涉及参数改变如降 `time_step` 必须记录 `agent_actions`。
- 任何 destructive 操作都不要自动执行，例如删除整个 run 目录。
- 三次同类失败后通知人工。

## 前端

前端应该展示真实运行态，而不是只展示配置壳。

前端主题要求：

- 默认主题保持当前科研业务风格，强调真实运行态、清晰数据密度、冷静的科技感和可读性。
- 右上角维护主题切换入口，可切换到暖色调“小猪模式”。
- 小猪模式可以参考 lulu 猪、pp 猪的日常、猪培根、小猪菊苣的温暖、可爱、日常感，但不要牺牲业务页面的信息层级和可读性。
- 小猪模式的视觉元素可以包含暖色背景、柔和状态色、可爱的插画或纹理；如果需要图标或背景，可以使用图片生成技能创建位图素材。
- 指针可以尝试变成猪蹄；如果影响 UI 可用性、浏览器兼容性或实现成本过高，可以先不做，把主题切换和页面可读性放在第一优先级。
- 主题实现要集中维护，例如统一 theme token、CSS 变量或主题上下文，避免在页面中零散硬编码颜色。

前端维护要求：

- 不允许为了兼容旧视觉而长期保留“旧实现 + 新实现”两套逻辑；确认测试没问题后，直接收敛成唯一实现。
- 不以零碎打补丁的方式堆叠样式覆盖；更新时应梳理现有组件和样式，只保留最有用、最清晰的实现。
- 每次前端更新后至少运行 `npm run build`；涉及交互或布局时，还要人工或自动化检查关键页面是否可用、文字是否溢出、按钮是否可点击。

优先页面：

1. Dashboard
   - 今日运行状态
   - FNL 覆盖情况
   - Slurm 队列状态
   - 最近错误和 Hermes/AI 动作
   - 最新产物入口

2. Run Detail
   - DAG 节点状态
   - 每个节点 progress、attempt、job id、日志入口
   - 手动 retry/cancel
   - 诊断建议

3. FNL Management
   - 按日期显示 FNL 缺失/已下载/已上传/服务器已校验
   - 手动下载和上传

4. Products
   - 地图产品、站点时间序列、CSV、图片
   - 历史预报结果查询

5. Scheduler
   - 每日自动任务配置
   - 预报窗口、季节、区域、variant
   - 通知配置

前端不要直接调用 SSH；所有操作经后端 API。

## 产物规范

每次成功运行应生成：

```text
runs/<run_id>/products/product_manifest.json
```

示例：

```json
{
  "run_id": "2026060400_spring_neimeng_official",
  "generated_at": "2026-06-04T20:00:00+08:00",
  "products": [
    {
      "type": "station_timeseries_csv",
      "name": "station_pollen_timeseries.csv",
      "path": "products/station_pollen_timeseries.csv",
      "mime": "text/csv"
    },
    {
      "type": "map_png",
      "name": "pollen_d02_24h.png",
      "path": "products/pollen_d02_24h.png",
      "mime": "image/png"
    },
    {
      "type": "geojson",
      "name": "pollen_contour_24h.geojson",
      "path": "products/pollen_contour_24h.geojson",
      "mime": "application/geo+json"
    }
  ]
}
```

产物下载到跳板机后，后端写入 `products` 表，前端只读后端索引。

当前实现状态：

- 后端已经支持按 `product_manifest.json` 下载、索引和提供产品文件下载。
- Products 页面已经能触发同步、筛选 run 产品并下载文件。
- 服务器 `product_extract.sh` 仍是模板，尚未从 `wrfout` 或后处理结果提取 NetCDF/GeoJSON/PNG。
- `package_products.sh` 当前只写空 manifest，尚未自动发现提取产物。
- Cesium 花粉分布页面目前使用模拟城市点位，尚未加载真实 NetCDF 或由 NetCDF 转出的可视化产品。

下一步推荐链路：

```text
wrfout / postprocess nc
  -> product_extract: 提取目标变量和时次，输出轻量 nc/geojson/png
  -> package_products: 写入 product_manifest.json
  -> backend sync-products: 下载到 runtime/products/<run_id> 并入库
  -> frontend Products / Map: 读取产品索引并渲染 GeoJSON/PNG/栅格层
```

前端不要直接读取服务器路径或原始大 NetCDF；若需要浏览器地图展示，应优先生成 GeoJSON、PNG overlay、GeoTIFF 切片或其他轻量产品。原始 `.nc` 可以作为下载归档产品同步，但不应作为第一版浏览器实时渲染格式。

## 分阶段实施路线

### Phase 0：梳理和约束

目标：不改核心运行逻辑，先建立共同语言。

- 新增本文件。
- 确认服务器 `auto-pollen` 部署路径。
- 确认 SSH 用户、Slurm 分区、FNL 服务器存放目录、产物下载目录。
- 确认每日预报窗口：起报时间、跑几天、用 FNL 还是后续 GFS/GDAS。

验收：

- 可以用一段命令说明每日流程从下载 FNL 到产物展示的责任边界。

### Phase 1：服务器状态化 MVP

目标：让现有脚本可被后端和 Hermes/AI CLI 稳定观测。

- 在 `auto-pollen` 下新增 `flow/`。
- 实现 `state.py`：原子写 JSON 状态和 events.jsonl。
- 实现 `flowctl status/logs/diagnose`。
- 包装 `auto_wrf.py --prep-only` 和 WRF sbatch，使其写状态。
- 包装 `copy_fnl.py --scan-only` 为 `flowctl fnl-verify`。
- 每个 run 创建 `runs/<run_id>/run_spec.json`。

验收：

- 跳板机 SSH 执行 `flowctl status --json` 能获得完整状态。
- 手动断开后重新执行 `flowctl status` 不依赖进程内存。

### Phase 2：跳板机后端接服务器

目标：后端从演示数据变为真实运行控制台。

- 实现 SSH 客户端。
- 新增 runs API。
- 后端调用服务器 `flowctl plan/submit/status/logs/retry`。
- SQLite 新增 `runs/run_nodes/run_events`。
- Dashboard 改为真实统计，不再使用写死值。

验收：

- 前端或 Swagger 能创建 run、提交 run、查看真实节点状态和日志。

### Phase 3：FNL 服务器优先校验和补齐闭环

目标：优先使用服务器已有 FNL；只有服务器缺失或损坏时，跳板机才自动补齐。

- 实现服务器 FNL 扫描接口，复用 `copy_fnl.py --scan-only` 或封装为 `flowctl fnl-verify`。
- 后端和 Hermes/AI CLI 先调用服务器扫描，拿到缺失/损坏清单。
- 实现跳板机 FNL 下载器。
- 只下载缺失或损坏的时次。
- 生成或更新 FNL manifest，记录来源和校验结果。
- 实现上传到服务器目录或 staging 目录。
- 上传后调用服务器校验。
- 数据库记录 FNL 文件状态。

验收：

- 服务器 FNL 完整时，不触发跳板机下载。
- 故意删除服务器某个 FNL，后端 repair 或 Hermes/AI CLI 能发现、下载/上传、服务器校验通过。
- 故意放置一个非 GRIB 或过小文件，后端 repair 或 Hermes/AI CLI 能识别损坏并只补该时次。

### Phase 4：Hermes/AI CLI 自动值守

目标：每日定时运行和有限自动重试。

- 通过后端 `agent/tick` API 和 CLI 快捷入口实现一次性 tick。
- 实现调度规则。
- 实现错误分类。
- 实现 retry policy。
- 实现通知 webhook。
- 记录每个 agent action。

验收：

- 一个完整每日 run 可无人值守完成。
- FNL 缺失、队列提交失败、postprocess 缺产物至少三类问题可自动恢复或通知。

### Phase 5：产物和前端业务化

目标：前端可展示预报结果和历史结果。

- 定义 product manifest。
- 后处理从 `wrfout` 或评估结果中提取目标花粉变量，生成轻量 `.nc` 归档、CSV、PNG、GeoJSON、GeoTIFF/切片等产品。
- 后端下载并索引产品。
- 前端 Run Detail 和 Products 页面展示真实产物。
- 前端地图优先渲染 GeoJSON/PNG overlay/栅格切片，不直接依赖服务器路径或原始大 NetCDF。
- 支持历史 run 查询。

验收：

- 前端能打开某次 run，看到 DAG、日志、诊断、产物和历史记录。
- 从服务器提取出的产品能写入 manifest，被跳板机下载索引，并在前端作为地图层或下载文件出现。

### Phase 6：更强 AI 诊断

目标：AI 可以基于 CLI 和状态文件辅助排障。

- 为常见错误建立诊断规则库。
- 为 AI 提供只读上下文打包命令：`flowctl collect-context`。
- 为 AI 提供受控动作：`retry-node`、`upload-fnl`、`restart-wrf`。
- 所有 AI 动作写入 `agent_actions`。

验收：

- AI 不需要直接翻服务器所有目录，只通过 CLI 就能获得关键诊断上下文。
- AI 建议和实际动作有审计记录。

## 近期最小可交付

建议下一步先做这 5 件事：

1. 根目录保留本 `AGENT.md`。
2. 在 `wrf-pollen/auto-pollen/flow/` 增加状态写入库和 `flowctl.py`。
3. 增加 `flowctl plan/status/fnl-verify/logs`，先不重构 DAG。
4. 后端增加 SSH 配置和 `/api/v1/runs/{run_id}/status`，直接读取服务器 `flowctl status --json`。
5. Hermes/AI 值守先只做监控和通知，不立刻自动改参数。

这样能最快把系统从“跑脚本”推进到“可被平台观测和接管”。

## 注意事项

- 不要删除现有 `auto-pollen` 运行脚本；先包装，后重构。
- 不要把服务器不能联网这件事藏在后端里；FNL 下载和上传必须是明确节点。
- 不要把日志解析当作唯一状态来源；日志用于诊断，状态文件用于控制。
- 不要让前端直接依赖服务器路径；统一通过后端和 product manifest。
- 不要把 FNL 写死为永久唯一数据源；未来真实预报可能需要接 GFS/GDAS。
- 不要让 AI 自动做不可逆操作；所有动作必须有限、可审计、可回滚或可人工接管。
