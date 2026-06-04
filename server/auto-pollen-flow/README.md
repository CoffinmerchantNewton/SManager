# auto-pollen-flow

服务器侧离线调度控制层。它不访问外网、不连接跳板机数据库，只负责：

- 生成 run spec。
- 校验服务器已有 FNL。
- 维护结构化状态文件。
- 生成 Slurm 节点脚本并按依赖提交。
- 暴露 `status/logs/diagnose/retry/products` CLI。

## 基本命令

```bash
python3 flowctl.py plan \
  --start 2026060400 \
  --end 2026060700 \
  --period spring \
  --domain neimeng \
  --variant official

python3 flowctl.py fnl-verify --run-id 2026060400_spring_neimeng_official
python3 flowctl.py status --run-id 2026060400_spring_neimeng_official --json
python3 flowctl.py submit --run-id 2026060400_spring_neimeng_official
```

## FNL 环境变量

```bash
export FNL_ROOT=/g1/COMMONDATA/glob/fnl
export FNL_FALLBACK_ROOT=/g7/anxq/Zhangjt/static/fnl
export FNL_MIN_MB=5
```

也可以用冒号分隔的多根目录：

```bash
export FNL_ROOTS=/g1/COMMONDATA/glob/fnl:/g7/anxq/Zhangjt/static/fnl
```

## 节点命令

`flowctl` 不写死 WPS/WRF 命令。生产运行时通过 `--commands-file` 传入节点命令：

```json
{
  "nodes": {
    "wps_ungrib": {
      "command": "bash /path/to/run_ungrib.sh",
      "slurm": {
        "partition": "normal",
        "nodes": 1,
        "ntasks": 1,
        "cpus_per_task": 4
      }
    }
  }
}
```

未配置命令的节点不会被提交；除非显式 `--allow-noop`，否则 `submit` 会拒绝执行。
