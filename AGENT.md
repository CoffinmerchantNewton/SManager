# SManager Agent Guide

本文是 SManager 后续开发和 AI 协作的主入口。当前目标不是继续加强本地控制面，而是把每日预报主链路收敛到 CentOS 服务器普通用户工作目录中，让本地机器只承担长期通信、FNL 补给、可视化和人工介入。

## 当前环境

- 本地办公电脑可以访问互联网，已准备 Docker、conda、Node.js。
- CentOS 服务器不能访问互联网，有 Slurm，可提交 WRF-Pollen 计算任务；网络可能短时不可达，但服务器自身通常仍在运行，极小概率重启。
- 服务器上已有一键运行脚本，能按当天日期和中国不同区域提交 WRF-Pollen 预报。
- 服务器已有 FNL/GFS 自动同步脚本，但 FNL 可能延迟、缺失或下载不完整。
- 服务器没有 system 权限，不能依赖 systemd 服务；常驻进程用 `nohup`、`screen` 或 `tmux`。
- 公网访问暂不纳入当前阶段，frp/公网域名/公开页面先不做。

## 核心目标

每日指定时间准时完成花粉预报。遇到本地电脑失效、网络断连、服务器重启、FNL 不完整、单个 Slurm 阶段失败等问题时，系统应尽量自动恢复；无法恢复时，也要降级到 GFS 或留下清晰状态，避免静默失败。

可靠性排序：

1. 准时提交并完成预报。
2. 优先使用本地修复后的 FNL，提高输入质量。
3. FNL 无法及时修复时自动降级 GFS。
4. 前端、AI、通知、公开访问都不能成为预报主链路的必要条件。

## 新架构边界

```text
本地办公电脑
  Docker tunnel service
  smanager-local backend/frontend
  FNL downloader/uploader
  optional AI observer

      long-lived tunnel / reverse channel

CentOS 服务器
  smanager-server daemon
  server workfolder FNL repair store
  Slurm prep -> wrf_run -> postprocess
  status/event/product manifests
```

### 服务器职责

服务器是主控端，负责：

- 定时创建每日预报任务。
- 按区域生成 run spec。
- 检查 FNL/GFS 输入。
- 发布 FNL repair request。
- 在 repair deadline 前等待本地补齐。
- deadline 到仍不可用时自动切 GFS。
- 提交 Slurm 三阶段任务：
  - prep：`geogrid.exe`、`link_grib.csh`、`ungrib.exe`、`metgrid.exe`、symbol link、`real.exe`、`compute-wrfchemi`
  - run：`mpirun -np 384 wrf.exe`
  - postprocess：Python 分析脚本
- 写结构化状态、事件、日志索引和产品 manifest。
- 网络断开或本地失效时仍可独立运行。

服务器端不得依赖：

- 外网访问。
- 本地后端在线。
- AI 在线。
- 公网服务。
- systemd root 权限。

### 本地职责

本地办公电脑是补给站和可视化端，负责：

- 用 Docker 启动长期通信/内网穿透服务，保持与服务器的控制通道。
- 轮询或接收服务器 FNL repair request。
- 从 NASA 或其他外网源下载缺失/损坏 FNL。
- 本地校验 FNL，再上传到服务器指定 workfolder。
- 展示 run 进度、FNL 状态、Slurm 阶段、日志、产品和告警。
- 手工触发受控动作，如重新上传 FNL、重试节点、取消 run。

本地不得成为每日预报的主调度器。即使本地完全关机，服务器也应按计划提交任务，并在必要时使用 GFS。

## 通信设计

当前阶段需要一个在本地 Docker 中长期运行的内网通信服务，不做公网暴露。

推荐形态：

```text
docker compose
  tunnel-daemon
    - 维护到服务器的长连接
    - 复用连接执行 API/文件同步
    - 断线自动重连

  smanager-local-api
    - 本地 FastAPI
    - 给前端提供状态缓存和人工操作入口

  smanager-frontend
    - 本地管理页面
```

优先实现轻量可靠方案：

- 通信控制面优先用 HTTP API。
- 大文件优先用 `rsync --partial` 或分片上传，必须支持断点和校验。
- 不再每条命令临时创建一次 SSH client。
- SSH 可以作为 tunnel 的底层连接，但业务代码不要散落临时 shell 命令和裸 SSH 客户端调用。

建议 tunnel 能力：

- 健康检查：心跳、最近成功通信时间、服务器 daemon 状态。
- API 转发：本地访问服务器 `smanager-server` 的状态和 repair request。
- 文件上传：FNL 上传到服务器 workfolder staging 目录。
- 自动重连：指数退避，记录断线和恢复事件。
- 本地缓存：服务器短时不可达时，前端仍能展示最近一次状态快照。

## 服务器常驻服务

由于没有 system 权限，服务器端用普通用户进程：

```bash
screen -S smanager-server
cd /path/to/SManager/server/smanager-server
nohup ./run_server.sh >> logs/serverd.out 2>&1 &
```

后续应提供：

```text
server/smanager-server/
  serverd.py              # 常驻 API 和调度循环
  scheduler.py            # 普通用户态定时器
  repair_requests.py      # FNL 修复请求状态机
  run_manager.py          # run 创建、提交、恢复、降级
  tunnel_api.py           # 与本地补给端通信的 API
  config.example.yaml
```

服务器 daemon 只做白名单业务动作，不提供任意 shell 执行接口。

必须支持：

- `tick`：扫描是否到预报时间，创建或推进 run。
- `reconcile`：扫描已有 run、Slurm job、状态文件，恢复 daemon 重启后的内存状态。
- `repair-request list/detail`：供本地查询缺失 FNL。
- `repair upload/verify/complete`：接收本地上传的 FNL 并二次校验。
- `status`：返回 workflow、node、FNL、产品摘要。
- `logs`：返回白名单日志尾部。

## FNL 策略

FNL 修复不得写入或覆盖服务器原始自动同步目录。

新增服务器 workfolder：

```text
$SMANAGER_WORK/
  fnl_repair/
    staging/
    verified/
      2026/
        20260616/
          fnl_20260616_00_00.grib2
```

取 FNL 时的优先级：

1. `$SMANAGER_WORK/fnl_repair/verified/...` 中本地修复并经服务器校验的 FNL。
2. 服务器自动同步的 FNL 主目录。
3. 服务器自动同步的 FNL 备用目录。
4. GFS fallback。

FNL 校验至少包括：

- 文件存在。
- 大小大于配置阈值。
- 文件头为 `GRIB`。
- 可选：`wgrib2` 能读 inventory。
- 上传后服务器端二次校验。

上传流程必须是：

```text
本地下载
  -> 本地校验
  -> 上传到 server staging
  -> 服务器校验
  -> atomic rename 到 verified
  -> 更新 repair request
```

不得直接向正式目录写半成品文件。

## FNL 主动同步

可以保留 FNL 主动同步，但它不是服务器主链路的前置条件。

本地可以定时预取未来需要的 FNL：

- 按每日预报窗口提前下载可能需要的时次。
- 下载后放入本地 cache。
- 若服务器 repair request 出现，优先从本地 cache 上传。
- 若服务器未请求，不主动覆盖服务器 verified 目录。

主动同步的目标是减少等待时间，不是替代服务器端 FNL 校验。

## Run 状态模型

服务器必须写结构化状态文件，供 daemon、本地后端、前端和 AI 读取：

```text
run_spec.json
workflow.status.json
state/<node>.status.json
events.jsonl
fnl_manifest.json
repair_requests.jsonl
products/product_manifest.json
```

日志只用于诊断，不能作为唯一状态源。

WRF 进度可以保持简单：

```text
(最后一个 wrfout 的预报时间 - 第一个 wrfout 的预报时间) / 总预报时长
```

如果只能可靠拿到文件名时间，就先用文件名；mtime 只用于估算生成速度和 ETA。

## 开发环境

### 本地

- Docker / Docker Compose：运行 tunnel、本地 API、前端和辅助服务。
- conda：运行本地 Python 工具、FNL 下载和调试脚本。
- Node.js：运行 React/Vite 前端。
- Python 后端：优先 FastAPI，复用现有 `backend/` 能力时要逐步瘦身。

常用本地命令应保持简单：

```bash
docker compose up -d tunnel local-api frontend
cd frontend && npm run dev
```

### 服务器

- 普通用户目录部署。
- 不要求 root，不要求 systemd。
- 使用 `screen`、`tmux` 或 `nohup` 保持 daemon。
- Slurm 提交仍通过 `sbatch --dependency=afterok`。
- 所有路径通过配置文件注入，不在代码中写死私有路径。

## 开发思路

1. 先保证服务器独立准点运行。
2. 再保证本地能补 FNL。
3. 再做可视化和人工操作。
4. 最后再考虑 AI 助手、公网访问、复杂通知。

每次开发都要问：

- 如果本地电脑关机，这个功能会不会阻塞服务器预报？
- 如果服务器短时连不上，本地是否能等待并恢复？
- 如果 daemon 重启，状态能否从文件和 Slurm 恢复？
- 如果 FNL 下载到一半，会不会污染正式输入？
- 如果重复点击或重复 tick，会不会重复提交大任务？

## 开发优先级

### P0：服务器主控闭环

- 新增服务器普通用户态 `smanager-server` daemon。
- 支持每日定时 tick。
- 支持 run 幂等创建。
- 支持 FNL 优先级扫描：repair verified -> server FNL -> fallback FNL -> GFS。
- 支持 repair deadline 和 GFS fallback。
- 支持 Slurm 三阶段依赖提交。
- 支持 daemon 重启后的 reconcile。

### P1：本地 Docker 通信和 FNL 补给

- 新增 Docker Compose。
- 新增 tunnel 服务，保持本地和服务器长期通信。
- 新增本地 FNL repair worker。
- 支持下载、校验、断点上传、服务器二次校验。
- 本地缓存 repair request 和最近状态。

### P2：前端监测和管理后台瘦身

- 首页展示 Python 分析结果和最新产品。
- 管理后台展示每个 run、区域、Slurm 阶段和 FNL 状态。
- 提供有限人工动作：重新上传 FNL、重试节点、取消 run、切换 GFS。
- 删除本地作为主调度器的旧页面或入口。

### P3：主动同步和自动诊断

- 本地提前同步可能需要的 FNL。
- 自动发现缺口并预填本地 cache。
- 规则化诊断常见错误。
- AI 只作为观察和建议，不进入准点提交主链路。

### P4：公网访问和更复杂运维

当前阶段不做。等内网闭环稳定后，再考虑 frp 公网暴露、认证加强、通知机器人和多用户。

## 删除和瘦身原则

项目噪声要低。旧方案里不再符合新边界的内容应删除或降级：

- 删除 `skills/` 下旧 AI skill，后续需要时重新设计。
- 删除或隐藏本地“主调度器”入口；本地只编辑服务器 schedule 或触发受控动作。
- 不再维护独立 AI agent。
- 不再让后端通过一次一 SSH 的方式承担核心调度。
- 不再新增多套状态模型，服务器 manifest 是事实源。
- 不再保留同时可用但语义冲突的新旧实现。
- 旧 `packages/`、`scripts/`、`server/auto-*`、临时 SSH/Paramiko 检查脚本和 SQLite 运行库都应删除。

如需保留兼容入口，必须在文档中明确标注 deprecated，并给出删除时间点。

## 安全边界

- 不提交 SSH 密码、NASA 凭据、token、服务器私有路径。
- 服务器 API 只暴露白名单动作。
- 文件上传必须限制目录，禁止路径穿越。
- 自动重试必须有限次数。
- 删除 run、覆盖已验证 FNL、修改生产配置后提交，都必须人工确认。

## 当前仓库改造方向

当前仓库保留：

- `backend/`：本地 MySQL API、状态缓存、产品/FNL 元数据和后续 tunnel 接入点。
- `frontend/`：本地监测和管理界面。
- `runtime/`：本地缓存、产物、日志和 manifest，不包含数据库文件。

后续推荐改法：

1. 新建干净的 `server/smanager-server`，不复用旧本地控制器实现。
2. 新建 Docker tunnel/FNL repair worker。
3. 继续瘦身 `backend/`：只做本地监控、补给 API 和 MySQL 元数据。
4. 瘦身 `frontend/`：围绕服务器事实源展示，不再假设本地掌控业务流程。
5. AI 操作规范等新架构稳定后再写。

最终系统要达到：服务器自己会按点跑，本地在线时会帮它用上更好的 FNL，本地离线时服务器也会自动降级完成预报。
