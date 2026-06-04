# Daily Forecast Runbook

本文描述跳板机每日花粉预报的标准操作。生产环境可以由外部 Hermes、cron 或 systemd timer 执行同样的 CLI。

## Preconditions

- 后端 `.env` 已配置 `SERVER_SSH_HOST`、`SERVER_FLOWCTL_PATH`、`SERVER_FLOW_ROOT`、`SERVER_FNL_ROOTS`、`SERVER_FNL_UPLOAD_DIR`。
- 内网服务器已部署 `server/auto-pollen-flow/`，并维护好生产 commands-file。
- `FNL_DOWNLOAD_COMMAND` 可在跳板机生成目标 FNL 文件。
- 如需机器人通知，配置 `NOTIFICATION_WEBHOOK_URL`；留空则不发送外部通知。

## One Tick

```bash
python3 packages/cli/smanager.py agent-tick \
  --start 2026060400 \
  --end 2026061100 \
  --period spring \
  --domain neimeng \
  --variant official \
  --commands-file /g7/anxq/Zhangjt/workspace/auto-pollen-flow/templates/run_spec/commands.auto_pollen.example.json \
  --dry-run-submit
```

确认 FNL、run spec 和 submit dry-run 无误后，生产调度再使用：

```bash
python3 packages/cli/smanager.py agent-tick \
  --start 2026060400 \
  --end 2026061100 \
  --period spring \
  --domain neimeng \
  --variant official \
  --commands-file /g7/anxq/Zhangjt/workspace/auto-pollen-flow/templates/run_spec/commands.auto_pollen.example.json \
  --real-submit
```

## Scheduled Task

查看已配置任务，并手动触发一次 dry-run：

```bash
python3 packages/cli/smanager.py tasks --limit 20
python3 packages/cli/smanager.py task-run --task-id <task_id>
```

确认 dry-run 无误后，才允许真实提交：

```bash
python3 packages/cli/smanager.py task-run --task-id <task_id> --real-submit
```

## Monitor

```bash
python3 packages/cli/smanager.py runs --limit 20
python3 packages/cli/smanager.py status --run-id <run_id>
python3 packages/cli/smanager.py events --run-id <run_id> --limit 100
python3 packages/cli/smanager.py diagnose --run-id <run_id> --summary
```

## Products

成功后同步和检查产物：

```bash
python3 packages/cli/smanager.py sync-products --run-id <run_id>
python3 packages/cli/smanager.py products --run-id <run_id> --status ready
```

地图页优先使用 `png_overlay_metadata` 和 `city_forecast_json`；不要为了首屏展示下载全部原始 `wrfout`。
