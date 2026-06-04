# Hermes-agent

Hermes-agent v1 是跳板机上的一次性自动值守命令，不直接 SSH 到服务器，只调用后端 API。

```bash
cd apps/hermes-agent
python -m hermes_agent tick \
  --start 2026060400 \
  --end 2026060412 \
  --period spring \
  --dry-run-submit
```

默认行为：

- 创建或刷新 run spec。
- 调用后端执行服务器 FNL 扫描。
- 必要时通过后端下载并上传缺失/损坏 FNL。
- FNL 就绪后调用后端提交 flow；默认 dry-run，不真实提交 Slurm。
- 自动动作由后端写入 `agent_actions` 表。
