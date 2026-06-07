# Lijt WRF-Chem Pollen User Guide

本文说明两件事：

1. Lijt 自己的 `/g7/anxq/pollen_predict` 工程原本如何跑北京秋季花粉预报。
2. 现在接入 Smanager 后，这条流程被拆成了哪些模块，以及如何运行。

本文以北京秋季 `pre7`、`2025-08-15 12:00` 起报、预报 7 天为例。

## 1. Lijt 原工程的运行方式

Lijt 工程根目录：

```text
/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7
```

关键脚本在：

```text
/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/program
```

主要脚本包括：

```text
program/total_auto_run_7.sh
program/auto_run_wps_fnl.sh
program/auto_run_wps_GFS.sh
program/auto_run_wrf.sh
program/cdo_pollen.sh
program/tranport.sh
```

### 1.1 原始总控脚本

入口脚本是：

```bash
cd /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/program
bash total_auto_run_7.sh
```

`total_auto_run_7.sh` 原本做的是按日期循环运行，核心参数包括：

```bash
start_date_str=20250801
end_date=20251015
predict_days=3
fnl_gfs=2
wrfchem_name=poll_BJ
```

注意：当前脚本文件名是 `total_auto_run_7.sh`，但脚本里 `predict_days=3`。实际跑 `pre7` 时需要保证 `predict_days=7`，并且对应目录使用：

```text
WPS_met_save_data/pre7days_12-12_${fnl_gfs}/${year}/${current_date}
WPS_met_save_data/wrfchemi_data_12-12_pre7/${year}
Beijing_wrfout_data_save_pre7/${year}/${current_date}
```

### 1.2 原始 WPS/FNL 步骤

脚本：

```text
program/auto_run_wps_fnl.sh
```

调用形式：

```bash
bash auto_run_wps_fnl.sh \
  20250815 \
  /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7 \
  /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/WRF-pollen/WPS-master \
  7 \
  2 \
  /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/WPS_met_save_data/pre7days_12-12_2/2025
```

它做的事情：

1. 用 `current_date - 2 days 12:00` 作为模拟开始时间。
2. 根据 `fnl_gfs` 决定 FNL 结束时刻。
3. 从 `/g1/COMMONDATA/glob/fnl/YYYY` 链接 `fnl_*` 文件到 WPS。
4. 修改 `namelist.wps`。
5. 运行 `geogrid.exe`、`ungrib.exe`、`metgrid.exe`。
6. 把生成的 `met_em.d01.*` 移到：

```text
WPS_met_save_data/pre7days_12-12_2/2025/20250815/
```

### 1.3 原始 WPS/GFS 步骤

脚本：

```text
program/auto_run_wps_GFS.sh
```

调用形式类似：

```bash
bash auto_run_wps_GFS.sh \
  20250815 \
  /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7 \
  /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/WRF-pollen/WPS-master \
  7 \
  2 \
  /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/WPS_met_save_data/pre7days_12-12_2/2025
```

它做的事情：

1. 根据 `fnl_gfs=2`，使用 `current_date - 1 day 18:00` 的 GFS 起点。
2. 从类似下面的目录链接 GFS：

```text
/g1/COMMONDATA/glob/gfs/2025/gfs.2025081418
```

3. 链接 `gfs.t18z.pgrb2.0p50.f000` 到 `f192`。
4. 修改 `namelist.wps`。
5. 跑 WPS 三个程序。
6. 把 GFS 段 `met_em.d01.*` 继续放入同一个 met 保存目录。

### 1.4 原始 wrfchemi 前置

从 Lijt 的主流程脚本可以确认：`total_auto_run_7.sh` 和 `auto_run_wrf.sh` 不负责生成 wrfchemi。

`auto_run_wrf.sh` 只是消费这个路径下已经存在的文件：

```text
/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/WPS_met_save_data/wrfchemi_data_12-12_pre7/2025/
```

文件名格式：

```text
wrfchemi_d01_YYYY-MM-DD_12_00_00.nc
```

例如 `2025-08-15` 起报时，WRF 实际从 `2025-08-13_12:00:00` 开始积分，所以需要：

```text
wrfchemi_d01_2025-08-13_12_00_00.nc
```

原来这一步等价于一个外部前置流程：

1. 在本地 Windows 或其他 Python 环境中运行 wrfchemi 生成脚本。
2. 计算温度前置、花粉释放、MEIC 化学排放底板。
3. 把花粉排放写入 MEIC wrfchemi。
4. 得到 `wrfchemi_d01_YYYY-MM-DD_12_00_00.nc`。
5. 上传到服务器 Lijt 工程的 `WPS_met_save_data/wrfchemi_data_12-12_preX/YYYY/` 目录。

在服务器上可参考的 wrfchemi 生成脚本位于：

```text
/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/Beijing_predict/auto_run_wrfchemi_predict_3_lijt/
```

其中包括：

```text
Beijing_auto_run_wrfchemi.py
Beijing_Autumn_pollen_predict.py
meic_Beijing_auto_run_wrfchemi.py
Beijing_add_pollen_emission.py
Beijing_add_pollen_emission_DL.py
```

### 1.5 原始 WRF 主流程

脚本：

```text
program/auto_run_wrf.sh
```

调用形式：

```bash
bash auto_run_wrf.sh \
  20250815 \
  /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7 \
  /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/WRF-pollen/WRF-pollen_Tot_Arte_Chen/test/em_real \
  7 \
  poll_BJ \
  /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/WPS_met_save_data/pre7days_12-12_2/2025
```

它做的事情：

1. 计算 WRF 起止时刻：
   - 起点：`current_date - 2 days 12:00`
   - 终点：`current_date + predict_days 12:00`
2. 找到已有 wrfchemi：

```text
WPS_met_save_data/wrfchemi_data_12-12_pre7/2025/wrfchemi_d01_2025-08-13_12_00_00.nc
```

3. 链接到 WRF 运行目录，链接名使用冒号格式：

```text
wrfchemi_d01_2025-08-13_12:00:00
```

4. 链接 `met_em.d01.*`。
5. 修改 `namelist.input`。
6. 运行 `real.exe`。
7. 用 `sbatch runwrf.sbatch` 提交 WRF-Chem 主作业。
8. 每 1800 秒检查一次 Slurm 队列。
9. 通过 `rsl.error.0000` 最后一行是否包含 `SUCCESS` 判断成败。
10. 成功后把 `wrfout_d01_*` 移到保存目录。
11. 清理 WRF 运行目录中的 `met_em`、`wrfchemi`、`wrfout`、`wrfrst`、`.err`、`.out`。

### 1.6 原始后处理和传输

点位提取脚本：

```text
program/cdo_pollen.sh
```

它使用 `cdo` 从保存后的 `wrfout` 中提取 `POLLEN_Tot`，示例点位为：

```text
lon=116.325 lat=39.945
```

传输脚本：

```text
program/tranport.sh
```

它会进入 `save_path`，用 `lftp` 把部分结果上传到：

```text
/cma/hf/
```

当前 crontab 中 Lijt 原工程还保留有定时传输项，例如：

```text
0 7 * 8-10 * /g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/program/tranport.sh
```

## 2. Smanager 接管后的模块拆分

新流程代码在本地：

```text
E:\SManager\server\auto-lijt-pollen
E:\SManager\server\auto-wrfchem-pollen
E:\SManager\server\auto-pollen-flow
```

部署到服务器后对应：

```text
/g7/anxq/Zhangjt/workspace/Smanager/auto-lijt-pollen
/g7/anxq/Zhangjt/workspace/Smanager/auto-wrfchem-pollen
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow
```

重要原则：

1. 远端工作目录固定为 `/g7/anxq/Zhangjt/workspace/Smanager/`。
2. 不修改 `/g7/anxq/pollen_predict` 原工程。
3. `prepare_case` 会把 Lijt 工程复制到 Smanager run 目录下再运行。
4. 不再复用已有 wrfchemi 成品；`generate_wrfchemi` 会自己生成。
5. Lijt 这条流程没有 Zhangjt 风格的独立 `compute_gdd` 节点。

## 3. 新流程模块

Smanager 配置文件：

```text
server/auto-lijt-pollen/commands.lijt_beijing_20250815_pre7.json
```

节点顺序：

```text
prepare_case
wps_fnl
wps_gfs
real
generate_wrfchemi
wrf_run
postprocess
product_extract
package_products
```

### 3.1 prepare_case

脚本：

```text
server/auto-lijt-pollen/bin/prepare_case.sh
```

作用：

1. 复制 Lijt 原工程的 `program` 和 `WRF-pollen` 到当前 run 目录。
2. 修正 WPS `geog_data_path`。
3. 创建 met、wrfchemi、wrfout 等输出目录。
4. 生成 `lijt_case.env`，给后续节点使用。
5. 清理复制出来的 WRF 运行目录中的旧链接和旧输出。

### 3.2 wps_fnl

脚本：

```text
server/auto-lijt-pollen/bin/run_wps_fnl.sh
```

作用：

1. 加载 Lijt WPS/WRF 所需 module。
2. 调用复制出来的 `program/auto_run_wps_fnl.sh`。
3. 生成 FNL 段 `met_em.d01.*`。

### 3.3 wps_gfs

脚本：

```text
server/auto-lijt-pollen/bin/run_wps_gfs.sh
```

作用：

1. 加载 Lijt WPS/WRF 所需 module。
2. 调用复制出来的 `program/auto_run_wps_GFS.sh`。
3. 生成 GFS 段 `met_em.d01.*`。

### 3.4 real

脚本：

```text
server/auto-lijt-pollen/bin/run_real.sh
```

作用：

1. 链接 `met_em.d01.*` 到复制出来的 WRF 运行目录。
2. 按起止时间修改 `namelist.input`。
3. 运行 `real.exe`。
4. 检查 `wrfinput_d01` 和 `wrfbdy_d01`。

### 3.5 generate_wrfchemi

脚本：

```text
server/auto-lijt-pollen/bin/generate_wrfchemi.sh
```

它调用通用 wrfchemi 链：

```text
server/auto-wrfchem-pollen/bin/run_wrfchemi_chain.sh
```

`run_wrfchemi_chain.sh` 内部顺序：

1. `make_temperature_inputs.py`
   - 读取 FNL/GFS。
   - 生成花粉模型需要的温度输入。
   - 对缺失的公开 FNL/GFS 时次做容错记录和填补。
2. `pollen_predict.py`
   - 运行北京秋季花粉释放/通量模型。
   - 输出到 `$FLOW_RUN_DIR/pollen_flux`。
3. `make_meic_wrfchemi.py`
   - 根据 `wrfinput_d01` 和 MEIC 数据生成化学排放底板。
4. `add_pollen_to_wrfchemi.py`
   - 把花粉排放写入 MEIC wrfchemi。
   - 输出：

```text
$FLOW_RUN_DIR/wrfchemi/wrfchemi_d01_YYYY-MM-DD_12_00_00.nc
```

随后 `generate_wrfchemi.sh` 会把这个文件复制到复制出来的 Lijt case 内：

```text
case/WRFChem_autumn_Beijing_pre7/WPS_met_save_data/wrfchemi_data_12-12_pre7/YYYY/
```

### 3.6 wrf_run

脚本：

```text
server/auto-lijt-pollen/bin/run_wrf.sh
```

作用：

1. 链接 `met_em.d01.*`。
2. 链接本流程生成的 wrfchemi。
3. 修改 `namelist.input`。
4. 动态生成 `runwrf.smanager.sbatch`。
5. 提交 WRF-Chem 主作业。
6. 等待 Slurm 作业结束。
7. 检查 `rsl.error.0000` 是否以 `SUCCESS` 收尾。
8. 成功后复制 `wrfout_d01_*` 到：

```text
$FLOW_RUN_DIR/wrfout/
```

### 3.7 postprocess

脚本：

```text
server/auto-lijt-pollen/bin/postprocess.sh
```

作用：

1. 检查 WRF 输出是否存在。
2. 检查 wrfchemi 是否存在。
3. 写出 Lijt 运行摘要。

### 3.8 product_extract

脚本：

```text
server/auto-pollen-flow/templates/node_commands/product_extract.sh
server/auto-pollen-flow/tools/product_extract.py
```

Lijt 使用的 WRF 输出变量不是 `POLLEN_1..POLLEN_9`，而是：

```text
POLLEN_Tot
POLLEN_Arte
POLLEN_Chen
POLL_Tot_Co
```

当前配置中使用：

```json
"PRODUCT_SUMMARY_VARIABLES": "POLLEN_Tot,POLLEN_Arte,POLLEN_Chen,POLL_Tot_Co,T2,U10,V10,RAINC,RAINNC,RAINSH",
"PRODUCT_SUMMARY_PRIMARY_VARIABLE": "POLLEN_Tot",
"PRODUCT_GEOJSON_VARIABLE": "POLLEN_Tot",
"PRODUCT_PNG_VARIABLE": "POLLEN_Tot"
```

输出目录：

```text
$FLOW_RUN_DIR/products/
```

### 3.9 package_products

脚本：

```text
server/auto-pollen-flow/templates/node_commands/package_products.sh
server/auto-pollen-flow/tools/package_products.py
```

作用：

1. 读取 `products/extracted_manifest.json`。
2. 生成 `products/product_manifest.json`。
3. 标记产品节点成功。

## 4. 如何运行现在的 Smanager 流程

在服务器执行：

```bash
cd /g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow
```

### 4.1 预检查

```bash
/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python flowctl.py preflight \
  --commands-file ../auto-lijt-pollen/commands.lijt_beijing_20250815_pre7.json
```

### 4.2 生成 run 计划

```bash
/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python flowctl.py plan \
  --run-id lijt_bj_20250815_pre7_smanager \
  --start 2025-08-15T12:00:00 \
  --end 2025-08-22T12:00:00 \
  --period autumn \
  --domain beijing \
  --variant lijt_autumn_pre7 \
  --met-provider fnl_gfs \
  --commands-file ../auto-lijt-pollen/commands.lijt_beijing_20250815_pre7.json
```

### 4.3 提交流程

```bash
/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python flowctl.py submit \
  --run-id lijt_bj_20250815_pre7_smanager
```

### 4.4 查看状态

```bash
/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python flowctl.py status \
  --run-id lijt_bj_20250815_pre7_smanager
```

### 4.5 重跑某个节点

如果某个节点失败，例如 `product_extract`：

```bash
/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python flowctl.py retry \
  --run-id lijt_bj_20250815_pre7_smanager \
  --node product_extract
```

## 5. 本次已跑通的结果

本次 run：

```text
lijt_bj_20250815_pre7_smanager
```

最终状态：

```text
success 100.0%
```

关键输出：

```text
runs/lijt_bj_20250815_pre7_smanager/wrfchemi/wrfchemi_d01_2025-08-13_12_00_00.nc
runs/lijt_bj_20250815_pre7_smanager/wrfout/wrfout_d01_2025-08-22_12:00:00
runs/lijt_bj_20250815_pre7_smanager/products/extracted/lijt_bj_20250815_pre7_smanager_POLLEN_Tot_summary.nc
runs/lijt_bj_20250815_pre7_smanager/products/extracted/lijt_bj_20250815_pre7_smanager_POLLEN_Tot_summary_POLLEN_Tot.geojson
runs/lijt_bj_20250815_pre7_smanager/products/extracted/lijt_bj_20250815_pre7_smanager_POLLEN_Tot_summary_POLLEN_Tot.png
runs/lijt_bj_20250815_pre7_smanager/products/product_manifest.json
```

## 6. 日常维护注意事项

### 6.1 不要把 Zhangjt compute_gdd 接到 Lijt 流程

Lijt 工程没有单独的 Zhangjt `compute_gdd` 节点。Smanager 中对应的前处理节点是：

```text
generate_wrfchemi
```

这个节点已经包含温度输入、花粉通量、MEIC、wrfchemi 合成。

### 6.2 不要直接污染 Lijt 原工程

新流程应该只写：

```text
/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/<run_id>/
```

不要把中间结果直接写回：

```text
/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7/
```

除非明确是在维护原始业务脚本。

### 6.3 清理旧 Slurm 作业

如果看到旧测试目录作业，需要取消：

```bash
squeue -u anxq -o '%i %j %T %M %R %Z'
```

凡是 `WORK_DIR` 包含下面路径的，都不是当前 Smanager 正式流程：

```text
/g7/anxq/Zhangjt/workspace/wrf-pollen-replace-lijt/
```

取消示例：

```bash
scancel <job_id>
```

### 6.4 行尾必须是 LF

Linux 上运行的 `.sh` 文件必须使用 LF 行尾。仓库已通过 `.gitattributes` 固定：

```text
*.sh text eol=lf
server/auto-pollen-flow/** text eol=lf
server/auto-lijt-pollen/** text eol=lf
```

如果 Bash 报错类似：

```text
set: pipefail\r: invalid option name
```

说明脚本被 CRLF 污染，需要重新归一化。

