# China Pollen Forecast System Frontend

基于 React + TypeScript + Vite 实现的中国全域花粉预报系统演示前端，参考了 `design_china_pollen_forecast_system` 中的 PRD、设计稿与交互方向。

## 已实现内容

- 预报门户大屏
  - Cesium 中国底图和行政边界
  - 最新 PNG overlay 产品层自动加载
  - GeoJSON/JSON 产品层回退加载
  - 重点城市点位和趋势分析兜底
- 管理员登录弹窗
  - 默认演示密码：`admin123`
- 预报管理中心
  - 调度、Slurm、成功率、系统健康度概览
  - 模块快捷入口和系统日志
- 流程编排
  - 模板列表
  - DAG 节点状态展示
  - 节点参数面板和执行日志
- 定时任务管理
  - 调度表格
  - 启停切换
  - 运行流水和完成态势
- 产品管理
  - 区域 / 状态 / 搜索筛选
  - 发布状态切换
  - 服务器产物同步和下载入口
- 主题
  - 默认科研风格
  - 右上角可切换暖色调小猪模式

## 启动方式

```bash
cd /Users/wangxu/projects/SManager/frontend
npm install
npm run dev
```

生产构建：

```bash
npm run build
```

## 当前实现边界

- 当前控制台已接入后端 API，但仍没有认证和权限系统。
- 花粉地图优先渲染后端已同步的 PNG overlay 或 GeoJSON 产品；没有可用产品时使用本地城市点位兜底。
- 原始 NetCDF 作为下载归档产品，不在浏览器直接渲染。
- 下一步建议优先补齐：
  - 认证与操作权限
  - Run Detail 产物、日志和诊断聚合视图
  - GeoTIFF/切片等更多地图层类型
