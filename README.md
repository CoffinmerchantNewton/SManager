# China Pollen Forecast System

## 2026-06-05 Implementation Status

本轮已按 README 未完成项完成仓库内实现，并按模块提交推送到 `origin/dev`。下方历史盘点中仍出现的“未完成”描述，以本状态块和新增运维文档为准：

- `feat(server)`: 生产 commands-file 模板、服务器 preflight、Slurm mock 和 flow 测试夹具已接入。
- `feat(backend)`: `.env` 单账号鉴权、bearer token、密码式 SSH、幂等 schema migration、storage cleanup、FNL repair 校验/审计已接入。
- `feat(cli)`: `login`、token 读取、`preflight`、`config-template`、`storage-cleanup`、批量 runs/products 和值守参数已接入。
- `feat(products)`: 正式城市/站点配置、风险阈值配置、等值线 GeoJSON、GeoTIFF capability fallback、增强 product manifest 已接入。
- `feat(frontend)`: 真实登录、axios bearer token、401 回登录、Portal 时间播放/图层/点选、Products/Run Detail manifest 展示已接入。
- `docs(ops)`: 生产拓扑、数据契约、安全、重试、日志轮转、磁盘清理、备份恢复和真实服务器验证 runbook 已补齐。

仍需现场确认的事项只剩两类：真实业务风险阈值需要业务侧校准；完整小窗口预报实跑需要在私有凭据、生产 commands-file 和服务器 preflight 通过后执行并记录结果。

基于 WRF-Pollen / WRF-Chem 的花粉扩散业务预报控制系统。当前 `dev` 分支的重点是把内网 CentOS 服务器上的离线 WPS/WRF/WRF-Pollen 运行流程，接入跳板机后端、CLI、前端和 Hermes/AI 辅助诊断控制面。

## 当前结论

- `apps/hermes-agent/` 已不再作为维护入口；Hermes 或 AI 助手统一通过 `packages/cli/smanager.py` 和 `skills/smanager-hermes-cli/SKILL.md` 调用后端 API。
- 服务器侧调度入口在 `server/auto-pollen-flow/`，负责 `plan/status/fnl-verify/submit/logs/events/diagnose/collect-context/retry/cancel/products`。
- 服务器节点脚本已改为可配置命令入口；WPS/WRF/后处理真实命令通过 commands-file 的 `*_COMMAND` 和 `*_CWD` 环境变量注入。
- 跳板机后端在 `backend/`，负责 SSH/local 调用服务器 flow、FNL 补齐、产物同步、运行事件入库、本地 storage 快照和前端 API。
- 诊断规则在 `packages/diagnostics/`，后端 diagnose/context 会返回 `analysis`，标识风险等级、推荐动作、是否允许自动处理和建议 CLI。
- 通知 webhook 默认关闭；配置 `NOTIFICATION_WEBHOOK_URL` 后，agent tick 失败或诊断要求人工时会发送 JSON 通知并写入 `agent_actions`。
- 前端已有管理控制台、Run/FNL/Products 页面和主题切换；花粉分布页会优先加载最新 PNG overlay 产品层和 `city_forecast_json` 城市预报，支持城市查询、未来 7 天时间轴、风险等级、主导物种、气温、降水和风速展示；缺产品时回退示例城市点位。
- 2026-06-05 本地跳板机验证已通过：`smanager` conda 环境和 Node/npm 可运行后端与 Vite 前端，Dashboard/Run Detail 能显示服务器真实 run `2026052100_spring_neimeng_official` 的进度、DAG 节点、日志尾部和诊断信息。
- `product_extract` 已支持按 `wrfout.txt` 对应的 WRF-Pollen 变量结构预提取 7 天小汇总 NetCDF，包含 `POLLEN_1..9`、气温、风、降水和派生的 `pollen_total`/主导物种/逐步降水；可继续生成城市 7 天预报 JSON、抽样点 GeoJSON、PNG overlay、等值线 GeoJSON，并在依赖可用时生成 GeoTIFF；缺少本地科学/GDAL 依赖时会写入明确 capability fallback 状态。启用 summary 后默认不再同步原始大 `wrfout`；XYZ/WMTS 切片留作后续性能增强。

## 各端进度盘点

### 服务器端 `server/auto-pollen-flow`

已完成：

- `flowctl` 已作为服务器唯一调度入口，覆盖 `plan/list/status/fnl-verify/submit/run-node/logs/events/diagnose/collect-context/retry/cancel/products`。
- 运行状态已落到结构化文件，节点状态包含进度、attempt、Slurm job id、错误码、日志路径等信息，后端和 CLI 可以稳定读取。
- FNL 校验只在服务器侧扫描本地目录，不联网下载；manifest 会标记 `missing/bad_magic/too_small/link_broken/server_ok` 和 `needs_repair`。
- DAG 节点脚本已拆出 WPS geogrid/ungrib/metgrid、real、GDD、pollen prep、WRF run、评估、产品提取、产品打包等步骤。
- 真实 WPS/WRF/后处理命令通过 commands-file 注入，节点脚本不再写死生产路径。
- `product_extract` 已支持生成轻量 `summary_netcdf`、`city_forecast_json`、抽样 GeoJSON、PNG overlay 和 overlay 元数据。
- 部署脚本已提供 `server/deploy/sync_to_server.sh` 和 `install_server_flow.sh`，用于同步服务器 flow 包。

未完成：

- 还没有填入生产 CentOS 服务器上的真实 commands-file，包括 WPS/WRF/WRF-Pollen 路径、模块加载、队列参数、业务区域参数。
- Slurm 真实集群上的端到端验证还没有完成，当前只能证明本地/脚本层逻辑可运行。
- 节点级资源参数、失败重试次数、超时策略仍偏基础，需要结合服务器队列经验校准。
- 产品层仍缺等值线、GeoTIFF、XYZ/WMTS 切片等更适合大范围连续场展示的产物。
- 还没有把完整生产 runbook 中的服务器目录、权限、日志轮转、磁盘清理策略固化成安装检查。

### 跳板机后端 `backend`

已完成：

- FastAPI 后端已接入服务器 `flowctl`，支持 local/SSH 两种执行模式。
- Runs API 已覆盖建 run、状态同步、提交、日志、事件、诊断、上下文、重试、取消、产物同步。
- FNL API 已实现服务器优先校验；缺失或损坏时调用 `FNL_DOWNLOAD_COMMAND` 在跳板机下载，再用 `rsync/scp` 上传服务器并二次校验。
- Products API 已支持产物列表、下载、JSON/GeoJSON/overlay 元数据 inline 读取、发布状态切换和删除。
- Scheduler API 已支持计划任务配置和手动触发 `agent tick`。
- Dashboard API 已聚合 run、FNL、products、agent actions、system logs 等运行态势。
- SQLite 模型已覆盖 workflow、run、node、event、FNL、product、scheduled task、agent action、system log 等核心元数据。
- 规则化诊断已接入 `packages/diagnostics`，后端 diagnose/context 会返回风险等级、建议动作、建议 CLI 和是否允许自动处理。
- 通知 webhook 可选配置，默认关闭；失败或需要人工处理时可写审计并发送 JSON 通知。

未完成：

- 还没有正式迁移框架，当前仍依赖 `Base.metadata.create_all`，后续需要 Alembic 或等价迁移方案。
- 认证授权仍是原型级，管理接口还没有生产级登录、角色、审计边界和密钥管理。
- 后端定时调度目前偏控制入口，生产上仍需要 systemd timer/cron/Hermes 调用策略落地。
- 文件存储仍是本地轻量目录控制器，缺清理策略、配额、归档、备份和大文件生命周期管理。
- 与真实 FNL 下载源的命令、凭据、失败退避策略尚未内置，只预留外部命令接口。
- 缺少面向真实服务器网络抖动、SSH 中断、Slurm 异常返回的集成测试。

### CLI 与 Hermes/AI 控制面 `packages/cli`、`skills/smanager-hermes-cli`

已完成：

- 不再维护独立 `apps/hermes-agent`；Hermes/AI/人工统一通过 CLI 调后端 API。
- CLI 已覆盖 doctor、storage、plan、runs、status、FNL verify/repair/coverage、submit、logs、events、diagnose、collect-context、retry/cancel、products、agent tick/actions、tasks/task-run。
- `diagnose --summary` 可输出更适合 AI 快速判断的诊断摘要。
- Skill 已说明 Hermes 如何巡检、补齐 FNL、提交/轮询、读取产品、诊断、重试和取消。
- 自动动作会写入 `agent_actions`，便于后端、前端和审计统一查看。

未完成：

- Hermes 的定时策略、值守频率、最大自动处理次数、人工确认边界还没有在生产环境固化。
- CLI 缺少更友好的批量操作、交互式选择、配置模板生成和生产环境预检向导。
- AI 自动恢复规则还比较保守，更多 WPS/WRF/WRF-Pollen 错误类型需要从真实日志中持续沉淀。

### 前端 `frontend`

已完成：

- 已有门户花粉分布页和管理控制台。
- Dashboard 展示运行态势、FNL 覆盖、最新产物、Hermes 动作和系统日志。
- Runs/Run Detail 可查看 run DAG、节点状态、诊断、事件、日志尾部、Hermes 动作和已同步产物下载入口。
- FNL 页面可查看覆盖状态并触发补齐流程。
- Products 页面可按 run 同步服务器产物、索引、下载和管理发布状态。
- Scheduler 页面可维护调度任务，并支持立即触发。
- Portal 使用 Cesium 展示中国区域，支持 PNG overlay、GeoJSON 回退、城市查询、未来 7 天时间轴、风险等级、主导物种、气温、降水和风速。
- Portal 已按 run 组织产品包，避免花粉底图和城市预报取到不同 run。
- 主题已集中为 `科研/小猪` 两套 token，Portal 和管理控制台都可切换。

未完成：

- Windy 风格仍只是基础方向，尚未实现完整的时间播放条、图层面板、风场粒子、色标单位联动、地图拾取点查询。
- 城市风险等级阈值仍需要业务校准，城市列表也需要替换为正式站点/城市配置。
- 前端还没有直接展示历史预报对比、历史曲线、站点实测对比和误差评估。
- 当前地图主要支持 PNG overlay/GeoJSON；大范围高性能瓦片、等值线和 GeoTIFF 还没接入。
- 管理端部分老页面存在 lint 历史问题，已改动的新 Portal/Layout/theme 文件可通过 lint，但全前端 lint 还需要单独清理。
- 登录鉴权仍是原型状态，生产 UI 需要真实认证、权限控制和会话处理。

### 契约、文档与测试

已完成：

- `packages/contracts` 已有 run spec、node status、workflow status、FNL manifest、product manifest、agent action、diagnosis analysis JSON Schema。
- 已有 FNL runbook、日常巡检 runbook、服务器 flow runbook、事故处理 playbook。
- 后端已有 scheduled task、diagnostics、notifications、contracts 等单元测试。
- 常用验证命令包括后端 compileall、后端 unittest、前端 build、局部前端 lint。

未完成：

- 契约还没有自动生成前端 TypeScript 类型或后端 Pydantic 模型。
- 缺少服务器 flow 的系统化 pytest 测试夹具，尤其是 Slurm mock、真实 product manifest、异常日志样本。
- 缺少端到端测试：创建 run -> FNL 校验/补齐 -> submit dry-run/真实提交 -> status -> product sync -> Portal 展示。
- 文档还缺生产部署拓扑、数据契约细节、重试策略和安全策略的最终版。

### 总体剩余里程碑

1. 填写并验证生产 commands-file，把真实 WPS/WRF/WRF-Pollen 路径、模块加载、Slurm 队列、区域和季节参数接入服务器 flow。
2. 在 CentOS 服务器上跑通一次完整 dry-run，再跑通一次真实小窗口预报：FNL 校验、WPS、WRF、产品提取、产物同步、前端展示。
3. 接入真实 FNL 下载命令和凭据管理，验证“服务器已有但可能损坏 -> 跳板机补齐上传 -> 二次校验”的闭环。
4. 完善产品体系：正式城市/站点配置、风险阈值、等值线/瓦片/GeoTIFF、历史预报归档和对比。
5. 完善生产运维：认证授权、通知机器人、定时任务、日志轮转、磁盘清理、备份恢复、部署检查。
6. 清理前端全仓库 lint 历史问题，补齐后端/服务器/前端端到端测试。

## 目录结构

```text
SManager/
  AGENT.md                         # 工程规划、实现约束、阶段路线
  backend/                         # FastAPI 跳板机后端
  frontend/                        # React/Vite 前端
  packages/
    cli/smanager.py                # Hermes/AI/人工共用 CLI
    contracts/                     # run/workflow/FNL/product/agent/diagnosis JSON 契约
  server/auto-pollen-flow/         # 部署到内网服务器的离线 flow 包装层
  skills/smanager-hermes-cli/      # Hermes/AI 调用 CLI 的 skill
  scripts/fake_fnl_download.py     # 本地 FNL 补齐闭环测试脚本
  runtime/                         # 跳板机本地运行时数据，不进 Git
  wrf-pollen/                      # WRF-Pollen 源码和既有 auto-pollen，当前不纳入本仓库提交
```

## 快速启动

建议使用已有 `joyagent` 环境运行后端：

```bash
conda activate joyagent
cd /Users/wangxu/projects/SManager
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd /Users/wangxu/projects/SManager/frontend
npm install
npm run dev
```

Windows 跳板机本地一键启动：

```bat
start_smanager.bat
```

该脚本会用 `smanager` conda 环境启动后端 `http://localhost:8000`，并启动前端 `http://localhost:5173`。只检查本地依赖、不打开服务窗口时可运行：

```bat
start_smanager.bat --check
```

CLI：

```bash
python3 packages/cli/smanager.py --api http://localhost:8000/api/v1 doctor
python3 packages/cli/smanager.py --api http://localhost:8000/api/v1 storage
python3 packages/cli/smanager.py --api http://localhost:8000/api/v1 runs --limit 20
```

## 跳板机配置

复制 `backend/.env.example` 到仓库根目录 `.env` 或 `backend/.env`，按部署环境修改：

```bash
DATABASE_URL="sqlite:///./runtime/db/pollen_forecast.sqlite"
SERVER_SSH_HOST="local"              # 生产环境改为内网服务器地址
SERVER_FLOWCTL_PATH="./server/auto-pollen-flow/flowctl.py"
SERVER_FLOW_ROOT="./runtime/server-flow"
SERVER_FNL_ROOTS="./runtime/server-fnl"
SERVER_FNL_UPLOAD_DIR="./runtime/server-fnl"
FNL_DOWNLOAD_COMMAND=""
JUMPBOX_FNL_CACHE_DIR="runtime/fnl"
JUMPBOX_PRODUCTS_DIR="runtime/products"
```

本地测试 FNL 补齐闭环时，可以将 `FNL_DOWNLOAD_COMMAND` 指向：

```bash
FNL_DOWNLOAD_COMMAND="python3 scripts/fake_fnl_download.py"
```

该脚本只生成以 `GRIB` 开头的合成文件，用于验证下载、上传和二次校验流程，不代表真实 FNL 数据源。

## 已实现控制面

服务器 flow：

- `flowctl plan/list/status`
- `flowctl fnl-verify`
- `flowctl submit/run-node`
- `flowctl logs/events/diagnose`
- `flowctl collect-context`
- `flowctl retry/cancel`
- `flowctl products`

后端 API：

- `GET/POST /api/v1/runs`
- `GET /api/v1/runs/{run_id}/status`
- `GET /api/v1/runs/{run_id}/logs`
- `GET /api/v1/runs/{run_id}/events`
- `GET /api/v1/runs/{run_id}/diagnose`
- `GET /api/v1/runs/{run_id}/context`
- `POST /api/v1/runs/{run_id}/submit`
- `POST /api/v1/runs/{run_id}/retry`
- `POST /api/v1/runs/{run_id}/cancel`
- `POST /api/v1/runs/{run_id}/sync-products`
- `POST /api/v1/fnl/verify-server`
- `POST /api/v1/fnl/repair`
- `GET /api/v1/fnl/coverage`
- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}/download`
- `GET /api/v1/products/{product_id}/content`
- `POST /api/v1/agent/tick`
- `GET /api/v1/agent/actions`
- `GET /api/v1/system/doctor`
- `GET /api/v1/system/storage`

CLI 常用入口：

```bash
python3 packages/cli/smanager.py doctor
python3 packages/cli/smanager.py storage
python3 packages/cli/smanager.py plan --start 2026060400 --end 2026060412 --period spring
python3 packages/cli/smanager.py runs --limit 20
python3 packages/cli/smanager.py status --run-id <run_id>
python3 packages/cli/smanager.py fnl-verify --run-id <run_id>
python3 packages/cli/smanager.py fnl-repair --run-id <run_id>
python3 packages/cli/smanager.py submit --run-id <run_id> --dry-run
python3 packages/cli/smanager.py events --run-id <run_id> --limit 100
python3 packages/cli/smanager.py diagnose --run-id <run_id>
python3 packages/cli/smanager.py diagnose --run-id <run_id> --summary
python3 packages/cli/smanager.py collect-context --run-id <run_id>
python3 packages/cli/smanager.py tasks --limit 20
python3 packages/cli/smanager.py task-run --task-id <task_id>
python3 packages/cli/smanager.py sync-products --run-id <run_id>
python3 packages/cli/smanager.py products --run-id <run_id>
python3 packages/cli/smanager.py product-content --product-id <geojson_or_overlay_metadata_product_id>
```

## 前端状态

- Dashboard 已接入真实 overview 聚合，展示运行态势、FNL 覆盖、最新产物、Hermes 动作和日志；Runs、FNL、Products、Scheduler、Workflow 等页面已存在。
- 右上角支持 `科研`/`小猪` 主题切换，主题 token 集中在 CSS 变量中维护。
- Run Detail 页面可以按 run 展示 DAG 节点、诊断、事件、日志尾部、Hermes 动作和已同步产物下载入口。
- 管理端登录状态已在当前浏览器会话内持久化，直接访问 `/admin/runs/<run_id>` 时登录后会回到原详情页；Run Detail 的事件列表 key 已避免同一时刻多节点事件导致的 React 重复 key 警告。
- Products 页面可以按 run 同步产物索引，并下载后端已同步到跳板机的产品文件。
- Cesium 花粉分布页面会尝试从 `/api/v1/products` 选择最新 `png_overlay_metadata` 和 `city_forecast_json` 产品；overlay 经 `/content` 读取 bounds 和 PNG 文件名，再用 `/download` 叠加 PNG，城市预报 JSON 用于城市查询、7 天时间轴、风险等级、主导物种、气温、降水和风速。没有产品时回退静态城市点位。

当前本地可视化验收记录：

- 后端 `http://localhost:8000` 健康检查正常，`/api/v1/system/doctor` 无 error；当前仅提示本地 `rsync` 未安装、`FNL_DOWNLOAD_COMMAND` 未配置。
- 前端 `http://localhost:5173` 可登录管理端，Dashboard 显示真实 run `2026052100_spring_neimeng_official` 为 `running`、总进度 `66.67%`。
- Run Detail 可展示 12 个 DAG 节点，其中 `wrf_run` 为 `running 1%`，`postprocess_eval`、`product_extract`、`package_products` 为 `ready`；页面无桌面端横向溢出。
- 管理端窄屏布局仍有横向溢出，主要来自侧栏和表格布局，后续可作为单独响应式优化项处理。

花粉分布展示仍需要下一步增强：

1. 城市风险阈值按业务标准校准，并增加站点/城市级历史对比。
2. 前端继续增加多图层切换、逐时播放和更多 Windy 风格交互。
3. 继续扩展等值线、GeoTIFF/切片等地图层类型。

不建议前端直接读取服务器路径或原始大 NetCDF；原始 `.nc` 更适合作为归档下载产品，地图首屏应通过后端产品索引和 manifest 暴露轻量可展示产品。已同步的 `.json/.geojson/.overlay.json` 产品可以通过 `/api/v1/products/{product_id}/content` 读取，PNG 等二进制产品通过 `/download` 读取。

## 验证命令

```bash
PYTHONPYCACHEPREFIX=/tmp/smanager-pycache conda run --no-capture-output -n joyagent \
  python -m compileall server/auto-pollen-flow backend/app packages/cli/smanager.py

cd frontend
npm run build
```

## 协作约束

- 所有本次实现只提交到 `dev`。
- 不提交 `runtime/`、FNL、WRF 输出、NetCDF 大文件。
- 不维护 `apps/hermes-agent` 第二套 agent 代码；Hermes/AI 走 CLI skill。
- 前端优化必须收敛为唯一实现，不长期保留新旧两套逻辑。
- 真实 WPS/WRF 命令放在 commands-file 或节点脚本中，不写死在后端 Python 里。
