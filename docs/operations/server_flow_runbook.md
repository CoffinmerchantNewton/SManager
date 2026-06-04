# Server Flow Runbook

## Deploy

From the jumpbox:

```bash
bash server/deploy/sync_to_server.sh user@server /g7/anxq/Zhangjt/workspace/auto-pollen-flow
```

`sync_to_server.sh` 会同步 `server/auto-pollen-flow/`，并在远端创建 `runs/`、`node_commands/`、`logs/`、`products/`。首次部署时，它会把 `templates/node_commands/*.sh` 复制到远端 `node_commands/`，之后可直接在 `node_commands/` 中维护服务器本地命令包装。

## Configure FNL

On the server:

```bash
export FNL_ROOTS=/g1/COMMONDATA/glob/fnl:/g7/anxq/Zhangjt/static/fnl
export FNL_MIN_MB=5
```

## Create a Run

```bash
python3 flowctl.py plan \
  --start 2026060400 \
  --end 2026060700 \
  --period spring \
  --domain neimeng \
  --variant official \
  --commands-file templates/run_spec/commands.auto_pollen.example.json
```

## Verify and Submit

```bash
RUN_ID=2026060400_spring_neimeng_official
python3 flowctl.py fnl-verify --run-id "$RUN_ID"
python3 flowctl.py status --run-id "$RUN_ID" --json
python3 flowctl.py submit --run-id "$RUN_ID" --dry-run
```

Remove `--dry-run` only after `node_commands/*.sh` have been replaced with real WPS/WRF commands.
