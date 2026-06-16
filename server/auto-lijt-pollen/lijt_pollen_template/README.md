# Lijt 完整手动模板

这个目录就是你要找的完整模板入口：

`/g7/anxq/Zhangjt/workspace/Smanager/auto-lijt-pollen/lijt_pollen_template`

它会直接生成一个可整体 `cp` 的工作包，里面包含：

- `batch_run.sh`
- `WPS/`
- `WRF/`
- `program/`
- `emission/`
- `scripts/`
- `static/`
- `output/`
- `logs/`
- `case.env`

## 目录约定

- `catalog.json`：模板源、静态资源、区域/季节配置清单
- `bin/stage_case.py`：生成完整 case
- `bin/run_step.sh`：执行通用步骤
- `bin/manual_run_all.sh`：一键串起通用步骤
- `work/`：你自己放手工 case 的地方

## 当前可用模板

| profile | 区域 | 季节 | 源模板 |
| --- | --- | --- | --- |
| `beijing_spring_pre7` | 北京 | 春 | `WRFChem_spring_Beijing_pre7` |
| `beijing_autumn_pre7` | 北京 | 秋 | `WRFChem_autumn_Beijing_pre7` |
| `yulin_spring_pre7` | 榆林 | 春 | `WRFChem_spring_Yulin_pre7` |
| `yulin_autumn_pre7` | 榆林 | 秋 | 当前服务器没有对应源模板 |
| `neimeng_spring_pre7` | 内蒙 | 春 | `WRFChem_spring_InnerMG_pre7` |
| `neimeng_autumn_pre7` | 内蒙 | 秋 | `WRFChem_autumn_InnerMG_pre7` |

## 完整 case 长什么样

每个 case 下面都会有：

- `WPS/`：完整 WPS 工作目录
- `WRF/`：完整 WRF 工作目录
- `program/`：Lijt 原始运行脚本目录
- `emission/`：排放模型完整目录
- `static/`：统一静态资源入口
- `scripts/`：通用手工执行脚本
- `output/`：所有输出落盘位置
- `logs/`：运行日志
- `case.env` 和 `lijt_case.env`

`static/` 里放的是统一静态资源入口，默认用软链指到服务器上的公共目录。

## 先生成一个完整 case

例如北京秋季：

```bash
cd /g7/anxq/Zhangjt/workspace/Smanager/auto-lijt-pollen/lijt_pollen_template
/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python bin/stage_case.py \
  --profile beijing_autumn_pre7 \
  --case-dir work/bj_20240815 \
  --start-date 20240815 \
  --predict-days 7 \
  --fnl-gfs 2
```

会生成：

- `work/bj_20240815/`
- `work/bj_20240815/static/`
- `work/bj_20240815/case.env`
- `work/bj_20240815/lijt_case.env`

然后你只改 `case.env` 里需要的参数，或者直接改模板里的脚本参数。

## 手工跑的顺序

通用步骤是：

1. `wps_fnl`
2. `wps_gfs`
3. `real`
4. `generate_wrfchemi`
5. `wrf_run`
6. `postprocess`

一键跑：

```bash
cd work/bj_20240815
bash batch_run.sh all
```

单步跑：

```bash
cd work/bj_20240815
bash batch_run.sh wps_fnl
```

## 三地区春秋怎么选

### 北京春

- profile：`beijing_spring_pre7`
- 模板源：`/g7/anxq/pollen_predict/WRFChem_spring_Beijing_pre7`
- 排放模型目录：`/g7/anxq/Zhangjt/workspace/pollen_forcast/Spring/Beijing_sim_2026/Beijing_predict/auto_run_wrfchemi_predict_3_lijt`

### 北京秋

- profile：`beijing_autumn_pre7`
- 模板源：`/g7/anxq/pollen_predict/WRFChem_autumn_Beijing_pre7`
- 排放模型目录：`/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/Beijing_sim/Beijing_predict/auto_run_wrfchemi_predict_3_lijt`

### 榆林春

- profile：`yulin_spring_pre7`
- 模板源：`/g7/anxq/pollen_predict/WRFChem_spring_Yulin_pre7`
- 排放模型目录：`/g7/anxq/Zhangjt/workspace/pollen_forcast/Spring/Yulin_sim_2026/Yulin_predict/auto_run_wrfchemi_predict_3_lijt`

### 榆林秋

当前服务器没有专门的榆林秋季源模板。不要直接拿北京或中国区模板硬替。要先补源模板，再把它加进 `catalog.json`。

### 内蒙春

- profile：`neimeng_spring_pre7`
- 模板源：`/g7/anxq/pollen_predict/WRFChem_spring_InnerMG_pre7`
- 排放模型目录：`/g7/anxq/Zhangjt/workspace/pollen_forcast/Spring/InnerMG_sim_2026/InnerMG_predict/auto_run_wrfchemi_predict_3_lijt`

### 内蒙秋

- profile：`neimeng_autumn_pre7`
- 模板源：`/g7/anxq/pollen_predict/WRFChem_autumn_InnerMG_pre7`
- 排放模型目录：`/g7/anxq/Zhangjt/workspace/pollen_forcast/Autumn/InnerMG_sim/InnerMG_predict/auto_run_wrfchemi_predict_3_lijt`

## 排放这一步怎么理解

手工跑 Lijt 时，`generate_wrfchemi` 这一步本质上是把：

- 物候参数
- PFT
- EF 面源
- MEIC
- 当前 `wrfinput`

拼成 `wrfchemi_d01_...nc`。

Smanager 里已经有一套改好的非 Windows 排放链：

`/g7/anxq/Zhangjt/workspace/Smanager/auto-wrfchem-pollen/bin/run_wrfchemi_chain.sh`

优先用它，不要再手动跑 Windows 路径版脚本。它会顺序调用：

1. `make_temperature_inputs.py`
2. `pollen_predict.py`
3. `make_meic_wrfchemi.py`
4. `add_pollen_to_wrfchemi.py`

所以在完整 case 里，排放默认直接跑：

```bash
cd work/bj_20240815
bash batch_run.sh generate_wrfchemi
```

但是要注意：这套 Smanager 非 Windows 链目前是按北京秋季三物种模型整理出来的，核心物种是：

- `TotPC`
- `Artemisia`
- `Chenopods`

它可以通过 `AREA`、`PARAM_ROOT`、`PFT_FILE`、`EF_ROOT`、`EF_CHEN_ROOT`、`POLLEN_*`、`TEMPERATURE_*` 去换区域范围和底板参数；比如“内蒙区域 + 北京秋季模型”这种混合任务可以直接用。

它不等价于已经完整参数化了所有春季/榆林/内蒙原始模型。春季脚本里常见的是 `N1/N2` 一类物种逻辑，和秋季 `Artemisia/Chenopods` 不是同一套。因此：

- 北京秋季：直接用 Smanager 非 Windows 链。
- 内蒙区域 + 北京秋季模型：直接用 Smanager 非 Windows 链，改区域网格和参数路径。
- 北京/榆林/内蒙春季：需要先确认或改造 `pollen_predict.py` 的物种逻辑，否则不要直接套秋季三物种脚本。
- 内蒙秋季原始模型：若只算 `TotPC` 或变量名不同，也需要确认变量名和 `add_pollen_to_wrfchemi.py` 是否匹配。

`emission/` 目录里是完整复制进来的区域脚本工作区，不是单独软链。你可以直接进去改参数再跑。

## 两个容易踩坑的点

1. `prepare_case` 不再是手动跑的必选入口，干净目录里是 `stage_case.py` 先建模板。
2. 秋季的 `Chenopods` 路径和春季的 `TotPC` 路径不一样，不要混着填。
