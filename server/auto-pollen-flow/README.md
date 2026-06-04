# auto-pollen-flow

服务器侧离线调度控制层。它不访问外网、不连接跳板机数据库，只负责：

- 生成 run spec。
- 校验服务器已有 FNL。
- 维护结构化状态文件。
- 生成 Slurm 节点脚本并按依赖提交。
- 暴露 `status/logs/diagnose/collect-context/retry/cancel/products` CLI。

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
python3 flowctl.py collect-context --run-id 2026060400_spring_neimeng_official
python3 flowctl.py submit --run-id 2026060400_spring_neimeng_official
python3 flowctl.py cancel --run-id 2026060400_spring_neimeng_official --dry-run
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

仓库自带的 `templates/node_commands/*.sh` 是通用节点入口，不再默认 `echo TODO` 成功退出。除 `product_extract`、`package_products` 外，节点必须配置对应命令变量，否则会以退出码 `2` 失败：

| 节点 | 命令变量 | 工作目录变量 |
| --- | --- | --- |
| `wps_geogrid` | `WPS_GEOGRID_COMMAND` | `WPS_GEOGRID_CWD` 或 `WPS_WORK_DIR` |
| `wps_ungrib` | `WPS_UNGRIB_COMMAND` | `WPS_UNGRIB_CWD` 或 `WPS_WORK_DIR` |
| `wps_metgrid` | `WPS_METGRID_COMMAND` | `WPS_METGRID_CWD` 或 `WPS_WORK_DIR` |
| `wrf_setup` | `WRF_SETUP_COMMAND` | `WRF_SETUP_CWD` |
| `real` | `REAL_COMMAND` | `REAL_CWD` 或 `WRF_RUN_DIR` |
| `compute_gdd` | `COMPUTE_GDD_COMMAND` | `COMPUTE_GDD_CWD` |
| `prep_pollen` | `PREP_POLLEN_COMMAND` | `PREP_POLLEN_CWD` |
| `wrf_run` | `WRF_RUN_COMMAND` | `WRF_RUN_CWD` 或 `WRF_RUN_DIR` |
| `postprocess_eval` | `POSTPROCESS_EVAL_COMMAND` | `POSTPROCESS_EVAL_CWD` |

命令变量会通过 `bash -lc` 执行，因此可以包含已有模块加载、`mpirun`、脚本参数和 shell 连接符。工作目录不存在时节点会失败，避免在错误目录里静默产出无效结果。

## 产物提取

`templates/node_commands/product_extract.sh` 默认调用 `tools/product_extract.py`：

- 默认扫描 run 目录下的 `*.nc` 和 `wrfout*`，复制到 `products/extracted/`。
- 可用 `PRODUCT_SOURCE_GLOB` 覆盖扫描规则，多个 glob 用 `:` 分隔。
- 设置 `PRODUCT_SUMMARY_PRESET=wrf_pollen` 后，会按 `wrfout` 中的真实 WRF-Pollen 变量抽取 `POLLEN_1..9`、`T2`、`U10`、`V10`、`RAINC`、`RAINNC`、`RAINSH`，生成一个小的 `summary_netcdf`；启用 summary 时默认不复制原始大 `wrfout`，除非显式设置 `PRODUCT_COPY_SOURCES=true`。
- `PRODUCT_SUMMARY_VARIABLES` 可用逗号或 `:` 指定自定义变量集；旧的 `PRODUCT_SUMMARY_VARIABLE` 单变量模式仍保留，用于非花粉或临时诊断。
- WRF-Pollen summary 会派生 `pollen_total`、`dominant_species_index`、`t2_c`、`wind10_ms`、`precip_accum_mm`、`precip_step_mm`，其中 `dominant_species_index` 对应 `POLLEN_1..9` 的致敏物种编号。
- `PRODUCT_SUMMARY_MAX_STEPS` 默认 `7`，适合 7 天预报；若输入是逐小时 `wrfout`，可用 `PRODUCT_SUMMARY_EVERY_NTH=24` 抽每天一个时间步。
- `PRODUCT_SUMMARY_VERTICAL_INDEX`、`PRODUCT_SUMMARY_3D_AXIS`、`PRODUCT_SUMMARY_STEP_HOURS`、`PRODUCT_SUMMARY_NAME`、`PRODUCT_SUMMARY_PRIMARY_VARIABLE` 可控制垂直层、三维变量解释、时间间隔、输出文件名和主变量；花粉模式默认主变量为 `pollen_total`。
- 设置 `PRODUCT_GEOJSON_VARIABLE` 后，会从 NetCDF 变量生成点 GeoJSON 产品。
- 设置 `PRODUCT_PNG_VARIABLE` 后，会从 NetCDF 变量生成 PNG overlay 和 `*.overlay.json` 元数据；`PRODUCT_OVERLAY_VARIABLE` 可作为同义配置。
- NetCDF 读取优先使用 `netCDF4`，否则使用 `scipy.io.netcdf_file`；可用 `PYTHON_BIN=/path/to/python` 指定带依赖的 Python。
- 经纬度变量默认按 `XLAT,XLAT_M,lat,latitude` 和 `XLONG,XLONG_M,lon,longitude` 查找，可用 `PRODUCT_LAT_VARIABLES`、`PRODUCT_LON_VARIABLES` 覆盖。
- `PRODUCT_TIME_INDEX`、`PRODUCT_VERTICAL_INDEX` 控制时间和垂直层切片。
- `PRODUCT_GEOJSON_MAX_POINTS` 或 `PRODUCT_GEOJSON_STRIDE` 控制 GeoJSON 抽样密度。
- `PRODUCT_PNG_MIN`、`PRODUCT_PNG_MAX`、`PRODUCT_PNG_ALPHA`、`PRODUCT_PNG_OPACITY` 控制 PNG 色带范围和地图透明度。

`templates/node_commands/package_products.sh` 会将提取结果写为 `products/product_manifest.json`，供跳板机后端 `sync-products` 下载和索引。
