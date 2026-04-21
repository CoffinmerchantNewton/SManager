# 中国花粉传播预报系统

基于 `Django + Celery + Slurm` 的花粉业务预报门户与自动化流程平台，一期聚焦以下能力：

- 中国全域 `d01/d02` 双域花粉传播预报展示
- 主页 WebGIS 地图、时间切换、花粉类别切换、固定分析图表
- 控制台流程模板、定时任务、运行监控、产物发布
- 轻量自研模板化 DAG，适配 `geogrid -> ungrib -> metgrid -> WPS -> 花粉预插值 -> WRF -> 后处理`
- Slurm 原生提交流程，支持模拟运行模式

## 技术栈

- Django 6
- Django REST Framework
- Celery
- django-celery-beat
- PostgreSQL / PostGIS（生产推荐）
- OpenLayers
- ECharts

## 快速开始

```bash
cp .env.example .env
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

打开：

- 首页：[http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- 控制台：[http://127.0.0.1:8000/console/login/](http://127.0.0.1:8000/console/login/)

默认控制台密码见 `.env` 中的 `CONSOLE_PASSWORD`。

## 业务流程

1. 在控制台创建流程模板，选择业务步骤和默认参数。
2. 创建定时任务，系统会同步为 `django-celery-beat` 周期任务。
3. Celery worker/beat 到点触发后创建 `WorkflowRun`。
4. `WorkflowExecutor` 生成步骤脚本、Slurm 脚本并提交任务。
5. 全链路成功后生成 `ForecastProduct` 与发布清单。
6. 管理员将某次成功运行发布到首页。

## 开发说明

- 开发环境默认 `SIMULATE_SLURM=True`，会用模拟作业快速走通业务闭环。
- 生产环境请关闭模拟模式，并保证 `sbatch`、`squeue`、`sacct` 可用。
- 当前代码使用 JSON/路径索引承载地图元数据，生产建议接 PostGIS 做边界与空间查询增强。
