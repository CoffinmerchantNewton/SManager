# SManager

SManager 是 WRF-Pollen 花粉预报的本地监测、FNL 补给和服务器调度辅助项目。

当前开发方向以 [AGENT.md](/Users/wangxu/projects/SManager/AGENT.md) 为准：服务器端负责每日准点预报主链路，本地电脑只负责 Docker 长连接、FNL 修复补给、可视化和人工介入。

## Current Architecture

```text
Local workstation
  Docker tunnel service
  local backend/frontend
  FNL downloader/uploader

      long-lived private channel

CentOS server
  smanager-server daemon
  user workfolder FNL repair store
  Slurm prep -> wrf_run -> postprocess
```

## Non-Goals For This Stage

- No public internet exposure.
- No public frp site.
- No standalone AI skill or agent.
- No local machine as the primary scheduler.
- No writes to the server's original FNL sync directory.

## Key Rules

- The server must be able to run forecasts without the local machine.
- Repaired FNL files live under the user's server workfolder and are preferred over server auto-synced FNL.
- If FNL repair misses the deadline, the server falls back to GFS and still submits the forecast.
- Server processes run as a normal user via `nohup`, `screen`, or `tmux`; do not assume systemd/root access.
- Large files stay out of the database. Store paths, manifests, hashes, sizes, and statuses.

## Important Paths

```text
backend/                  # Local FastAPI backend, MySQL only
frontend/                 # Existing local frontend
runtime/                  # Local runtime cache, products, logs, manifests
```

Planned server-side addition:

```text
server/smanager-server/   # User-mode server daemon for schedule, repair requests, reconcile, and status API
```

## Development Priority

1. Build the server-side daemon and make daily forecast submission independent of the local machine.
2. Add the local Docker tunnel and FNL repair worker.
3. Slim the frontend/backend into monitoring, product display, and controlled manual actions.
4. Add proactive FNL prefetching.
5. Reintroduce AI/public access only after the private server-first loop is stable.

Read [AGENT.md](/Users/wangxu/projects/SManager/AGENT.md) before making architectural changes.
