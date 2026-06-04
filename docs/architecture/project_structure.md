# Project Structure

本文描述 SManager 的目标目录架构。当前仓库仍保留原有 `backend/`、`frontend/`、`wrf-pollen/` 路径；后续优化时按本文逐步迁移，不做一次性大搬家。

## 分层

```text
SManager/
  apps/                 # 跳板机运行的应用：后端、前端；不再维护独立 Hermes-agent
  packages/             # 跨应用共享的契约、CLI、诊断规则和公共 Python 包
  server/               # 部署到内网服务器的 flow 包装层
  runtime/              # 跳板机本地运行数据，不进 Git
  docs/                 # 架构和运维文档
  wrf-pollen/           # WRF-Pollen 模式源码和现有 auto-pollen
```

## apps

```text
apps/
  backend/
  frontend/
```

`backend` 负责 API、数据库、SSH 调用、FNL 管理、产物索引和通知。

`frontend` 只调用后端 API，不直接访问服务器路径。

外部 Hermes、cron 或 systemd timer 通过 `packages/cli/smanager.py` 调用后端 API，负责每日值守、轮询状态、补 FNL、自动重试和通知；业务逻辑保留在后端 service 中。

## packages

```text
packages/
  contracts/
  cli/
  diagnostics/
  python/
```

`contracts` 存放 `run_spec`、节点状态、workflow 状态、FNL manifest、产品 manifest、agent action、diagnosis analysis 等 JSON Schema。

`diagnostics` 存放错误模式和恢复动作，供后端、CLI 和 AI 助手共用。

`cli` 提供跳板机统一控制入口 `smanager`。

`python` 存放共享 Python 包，例如时间、路径、JSON 原子写等公共工具。

## server

```text
server/
  auto-pollen-flow/
    flowctl.py
    nodes/
    lib/
    templates/
  deploy/
```

`auto-pollen-flow` 是服务器侧离线 flow 包装层。它不访问外网，不连接跳板机数据库，只通过状态文件和 CLI 对外暴露能力。

`flowctl.py` 是服务器唯一稳定入口，后端通过它提交、查询、诊断和重试任务；AI 助手通过后端 CLI 间接调用，不直接 SSH 绕过控制面。

## runtime

```text
runtime/
  db/
  fnl/
  products/
  logs/
  manifests/
  cache/
```

`runtime` 存放跳板机本地运行态数据，默认不进 Git。数据库只保存元数据和索引，大文件保存在文件系统中。

## 迁移顺序

1. 新建 `server/auto-pollen-flow`，包装现有 `wrf-pollen/auto-pollen`。
2. 建立 `packages/contracts`，统一状态和 manifest 字段。
3. 后端先接 `flowctl status --json`，再接 submit/retry/logs。
4. 外部 Hermes/AI CLI 先做只读监控和通知，再开放自动重试。
5. 前端新增 Run Detail、FNL Management、Products 页面。
6. 等真实 API 稳定后，再把旧 `backend/` 和 `frontend/` 迁入 `apps/`。
