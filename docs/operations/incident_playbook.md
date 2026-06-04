# Incident Playbook

本文给人工和 AI 助手使用。所有操作优先走 CLI/API，避免直接修改服务器运行目录。

## First Look

```bash
python3 packages/cli/smanager.py diagnose --run-id <run_id> --summary
python3 packages/cli/smanager.py collect-context --run-id <run_id> --tail 160 --event-limit 120 --max-logs 12
python3 packages/cli/smanager.py agent-actions --run-id <run_id> --limit 50
```

读取 `analysis.summary`：

- `auto_retry_allowed=true`：可以按建议执行 dry-run 动作。
- `requires_operator=true`：不要真实重试，先处理配置、磁盘、模型参数或通知人工。

## Safe Actions

FNL 问题：

```bash
python3 packages/cli/smanager.py fnl-repair --run-id <run_id>
```

节点重试必须先 dry-run：

```bash
python3 packages/cli/smanager.py retry-node --run-id <run_id> --node <node>
```

dry-run 确认无误后才允许：

```bash
python3 packages/cli/smanager.py retry-node --run-id <run_id> --node <node> --real
```

## Stop Conditions

以下情况停止自动重试：

- `analysis.summary.requires_operator=true`
- 磁盘满、配额不足、节点命令缺失
- WRF CFL 或段错误尚未人工确认 restart/timestep 策略
- 同一节点同类错误重复三次

## Notifications

默认不会向外发送通知。若跳板机后端配置了 `NOTIFICATION_WEBHOOK_URL`，`agent-tick` 在失败或诊断要求人工介入时会发送 JSON webhook，并在 `agent_actions` 中记录 `notification` 动作。

## Product Issues

产品缺失时先看：

```bash
python3 packages/cli/smanager.py logs --run-id <run_id> --node product_extract --tail 300
python3 packages/cli/smanager.py products --run-id <run_id>
```

如果 `summary_netcdf` 已生成但地图没有图层，检查 `png_overlay_metadata` 和 `city_forecast_json` 是否同步到后端。
