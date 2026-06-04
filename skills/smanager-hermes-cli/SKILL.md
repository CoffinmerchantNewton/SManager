---
name: smanager-hermes-cli
description: 当 Hermes 或 AI 助手需要通过跳板机 CLI 操作 SManager 花粉预报系统、查看 run/FNL/产物状态，或安全扩展 CLI/后端控制面且不改 Hermes-agent 内部代码时使用。
---

# SManager Hermes CLI

把跳板机 CLI 当作 Hermes 的控制面。不要直接 SSH 到 CentOS 服务器，也不要修改 `apps/hermes-agent/`，除非用户明确要求改 Hermes-agent 代码。

所有命令从仓库根目录执行：

```bash
python3 packages/cli/smanager.py --api "${SMANAGER_API:-http://localhost:8000/api/v1}" <command>
```

## 核心流程

1. 创建或刷新一次运行：

```bash
python3 packages/cli/smanager.py plan \
  --start 2026060400 \
  --end 2026060412 \
  --period spring \
  --domain neimeng \
  --variant official \
  --met-provider FNL
```

2. 先检查服务器侧 FNL：

```bash
python3 packages/cli/smanager.py fnl-verify --run-id <run_id>
```

只有服务器 manifest 报告文件需要修复时才执行补齐。后端 repair 会处理下载、本地 GRIB 校验、上传和服务器二次校验。

```bash
python3 packages/cli/smanager.py fnl-repair --run-id <run_id>
```

3. 先做安全提交预检：

```bash
python3 packages/cli/smanager.py submit --run-id <run_id> --dry-run
```

确认 dry-run 输出无问题后，真实提交：

```bash
python3 packages/cli/smanager.py submit --run-id <run_id>
```

4. 轮询状态和日志：

```bash
python3 packages/cli/smanager.py status --run-id <run_id>
python3 packages/cli/smanager.py logs --run-id <run_id> --node <node_name> --tail 200
python3 packages/cli/smanager.py diagnose --run-id <run_id>
```

5. 同步完成后的预报产物：

```bash
python3 packages/cli/smanager.py sync-products --run-id <run_id>
python3 packages/cli/smanager.py products --run-id <run_id>
python3 packages/cli/smanager.py product-download --product-id <product_id> --output runtime/downloads/product.dat
```

## 单次 Tick

`agent-tick` 只作为后端 API 的 CLI 快捷入口使用。把它视为一次 CLI 操作，不要因此接管 Hermes-agent 代码。

```bash
python3 packages/cli/smanager.py agent-tick \
  --start 2026060400 \
  --end 2026060412 \
  --period spring \
  --dry-run-submit
```

只有 dry-run 输出可接受后，才使用 `--real-submit`。

## 查看命令

- 查看运行诊断：

```bash
python3 packages/cli/smanager.py diagnose --run-id <run_id>
```

- 查看 FNL 数据库覆盖情况：

```bash
python3 packages/cli/smanager.py fnl-coverage --start 2026060400 --end 2026060412
python3 packages/cli/smanager.py fnl-coverage --status server_ok
python3 packages/cli/smanager.py fnl-coverage --repair-only --limit 100
```

- 查看自动动作审计：

```bash
python3 packages/cli/smanager.py agent-actions --run-id <run_id> --limit 50
python3 packages/cli/smanager.py agent-actions --action-type fnl_repair --status error
```

- 查看或下载已同步产物：

```bash
python3 packages/cli/smanager.py products --run-id <run_id> --status ready
python3 packages/cli/smanager.py product-download --product-id <product_id>
```

- 查看服务器节点日志：

```bash
python3 packages/cli/smanager.py logs --run-id <run_id> --tail 300
```

## 受控修改

节点重试必须先 dry-run：

```bash
python3 packages/cli/smanager.py retry-node --run-id <run_id> --node <node_name> --dry-run
```

dry-run 只用于验证动作计划，不应改变服务器节点状态。

只有诊断输出和 dry-run 输出都确认无误后，才允许真实重试：

```bash
python3 packages/cli/smanager.py retry-node --run-id <run_id> --node <node_name> --real
```

取消运行也必须先 dry-run：

```bash
python3 packages/cli/smanager.py cancel-run --run-id <run_id> --dry-run
```

只有确认 dry-run 列出的节点和 Slurm job 确实应该停止后，才允许真实取消：

```bash
python3 packages/cli/smanager.py cancel-run --run-id <run_id> --real
```

## 读取结果

除 `logs` 输出文本外，CLI 命令默认输出 JSON。优先读取这些字段：

- `ok`: API 总体结果。
- `data.run_id`: 生成或选择的运行 ID。
- `data.fnl.final.ok`: repair/tick 输出中的 FNL 复验结果。
- `data.submit.dry_run`: 是否真实提交 Slurm。
- `data.status.status` 和 `data.status.progress`: 运行状态。
- `data.products.indexed_count` 或产物同步结果：已索引产物。

当命令输出 JSON 且顶层 `ok` 为 `false` 时，CLI 退出码应为非零；自动化脚本应同时检查退出码和 `ok` 字段。

如果 FNL 状态是 `server_ok`，不要下载或上传。只有 `missing`、`bad_magic`、`too_small`、`link_broken` 需要进入补齐。

## 修改控制面

当用户要求调整 Hermes 操作能力时，优先修改 CLI 或后端 API 契约，而不是修改 Hermes-agent 代码。

相关文件：

- `packages/cli/smanager.py`: CLI commands and arguments.
- `backend/app/api/runs.py`: run lifecycle endpoints.
- `backend/app/api/fnl.py`: FNL verify/repair/coverage endpoints.
- `backend/app/api/agent.py`: tick and action audit endpoints.
- `backend/app/services/flow/server_flow.py`: bridge to server `flowctl`.
- `server/auto-pollen-flow/flowctl.py`: server-side scheduling/status/FNL commands.

保持 CLI 输出为机器可读 JSON。修改面向自动化的命令行为时，明确失败必须返回非零退出码。

## 安全规则

- 不要 stage 或 commit 无关本地改动。
- WPS/WRF 命令继续放在 commands-file 模板中，不要在 Python 里写死服务器路径。
- 服务器 FNL 校验是权威来源；只有服务器校验报告可修复文件后，跳板机才下载。
- 代码改动后运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/smanager-pycache python3 -m compileall server/auto-pollen-flow backend/app packages/cli/smanager.py
```

如果改了前端文件，再运行：

```bash
cd frontend && npm run build
```
