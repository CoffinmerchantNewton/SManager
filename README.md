# China Pollen Forecast System

基于 WRF-Pollen / WRF-Chem 的花粉扩散业务预报控制系统。当前 `dev` 分支的重点是把内网 CentOS 服务器上的离线 WPS/WRF/WRF-Pollen 运行流程，接入跳板机后端、CLI、前端和 Hermes/AI 辅助诊断控制面。

## 当前结论

- `apps/hermes-agent/` 已不再作为维护入口；Hermes 或 AI 助手统一通过 `packages/cli/smanager.py` 和 `skills/smanager-hermes-cli/SKILL.md` 调用后端 API。
- 服务器侧调度入口在 `server/auto-pollen-flow/`，负责 `plan/status/fnl-verify/submit/logs/events/diagnose/collect-context/retry/cancel/products`。
- 服务器节点脚本已改为可配置命令入口；WPS/WRF/后处理真实命令通过 commands-file 的 `*_COMMAND` 和 `*_CWD` 环境变量注入。
- 跳板机后端在 `backend/`，负责 SSH/local 调用服务器 flow、FNL 补齐、产物同步、运行事件入库、本地 storage 快照和前端 API。
- 前端已有管理控制台、Run/FNL/Products 页面和主题切换；花粉分布页会优先加载最新 PNG overlay 产品层，回退 GeoJSON/JSON 产品层，再回退模拟城市点位。
- `product_extract` 已支持按 glob 扫描服务器 run 目录中的 `.nc`/`wrfout*` 文件，并可预提取 7 天花粉小汇总 NetCDF、抽样点 GeoJSON 与 PNG overlay；启用 summary 后默认不再同步原始大 `wrfout`；等值线、GeoTIFF/切片仍待实现。

## 目录结构

```text
SManager/
  AGENT.md                         # 工程规划、实现约束、阶段路线
  backend/                         # FastAPI 跳板机后端
  frontend/                        # React/Vite 前端
  packages/
    cli/smanager.py                # Hermes/AI/人工共用 CLI
    contracts/                     # run/FNL/product JSON 契约
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
python3 packages/cli/smanager.py collect-context --run-id <run_id>
python3 packages/cli/smanager.py sync-products --run-id <run_id>
python3 packages/cli/smanager.py products --run-id <run_id>
python3 packages/cli/smanager.py product-content --product-id <geojson_or_overlay_metadata_product_id>
```

## 前端状态

- Dashboard 已接入真实 overview 聚合，展示运行态势、FNL 覆盖、最新产物、Hermes 动作和日志；Runs、FNL、Products、Scheduler、Workflow 等页面已存在。
- 右上角支持 `科研`/`小猪` 主题切换，主题 token 集中在 CSS 变量中维护。
- Run Detail 页面可以按 run 展示 DAG 节点、诊断、事件、日志尾部、Hermes 动作和已同步产物下载入口。
- Products 页面可以按 run 同步产物索引，并下载后端已同步到跳板机的产品文件。
- Cesium 花粉分布页面会尝试从 `/api/v1/products` 选择最新 `png_overlay_metadata` 产品，经 `/content` 读取 bounds 和 PNG 文件名，再用 `/download` 叠加 PNG；没有 overlay 时回退 GeoJSON/JSON 产品，最后使用静态城市点位和模拟浓度。

真实花粉分布展示还需要下一步实现：

1. 在 `product_extract` 中继续扩展等值线、GeoTIFF/切片等可视化产品。
2. 后端 `sync-products` 下载并索引这些产品。
3. 前端继续扩展 GeoTIFF/切片等地图层类型。

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
