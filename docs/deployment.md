# 部署说明

## 推荐拓扑

- `Nginx`
- `Django (gunicorn)`
- `Celery worker`
- `Celery beat`
- `PostgreSQL/PostGIS`
- `Redis`
- `Slurm client tools`

以上组件部署在同一套受控业务环境中，通过共享目录访问：

- `data/runs`
- `data/products`
- `data/logs`

## 生产配置建议

- 使用 `POSTGRES_*` 环境变量切换到 PostgreSQL。
- 关闭 `SIMULATE_SLURM`。
- 使用 Nginx 直接代理 `/static/`、`/media/` 与产品瓦片目录。
- 通过 `manage.py check --deploy` 做 Django 生产配置检查。
- 控制台密码放入外部 secret 管理，不写死在镜像中。

## Celery 进程

```bash
celery -A config worker -l info
celery -A config beat -l info
```

## Slurm 对接

系统默认通过以下命令与 Slurm 交互：

- `sbatch`
- `squeue`
- `sacct`

如果集群要求额外模块加载或代理提交，建议在 `WorkflowExecutor` 或 `SlurmClient` 中替换批处理脚本模板。
