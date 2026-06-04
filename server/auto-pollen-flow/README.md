# auto-pollen-flow

服务器侧离线调度控制层。它不访问外网、不连接跳板机数据库，只负责：

- 生成 run spec。
- 校验服务器已有 FNL。
- 维护结构化状态文件。
- 生成 Slurm 节点脚本并按依赖提交。
- 暴露 `status/logs/diagnose/retry/cancel/products` CLI。

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

## 产物提取

`templates/node_commands/product_extract.sh` 默认调用 `tools/product_extract.py`：

- 默认扫描 run 目录下的 `*.nc` 和 `wrfout*`，复制到 `products/extracted/`。
- 可用 `PRODUCT_SOURCE_GLOB` 覆盖扫描规则，多个 glob 用 `:` 分隔。
- 设置 `PRODUCT_GEOJSON_VARIABLE` 后，会从 NetCDF 变量生成点 GeoJSON 产品。
- 设置 `PRODUCT_PNG_VARIABLE` 后，会从 NetCDF 变量生成 PNG overlay 和 `*.overlay.json` 元数据；`PRODUCT_OVERLAY_VARIABLE` 可作为同义配置。
- NetCDF 读取优先使用 `netCDF4`，否则使用 `scipy.io.netcdf_file`；可用 `PYTHON_BIN=/path/to/python` 指定带依赖的 Python。
- 经纬度变量默认按 `XLAT,XLAT_M,lat,latitude` 和 `XLONG,XLONG_M,lon,longitude` 查找，可用 `PRODUCT_LAT_VARIABLES`、`PRODUCT_LON_VARIABLES` 覆盖。
- `PRODUCT_TIME_INDEX`、`PRODUCT_VERTICAL_INDEX` 控制时间和垂直层切片。
- `PRODUCT_GEOJSON_MAX_POINTS` 或 `PRODUCT_GEOJSON_STRIDE` 控制 GeoJSON 抽样密度。
- `PRODUCT_PNG_MIN`、`PRODUCT_PNG_MAX`、`PRODUCT_PNG_ALPHA`、`PRODUCT_PNG_OPACITY` 控制 PNG 色带范围和地图透明度。

`templates/node_commands/package_products.sh` 会将提取结果写为 `products/product_manifest.json`，供跳板机后端 `sync-products` 下载和索引。
