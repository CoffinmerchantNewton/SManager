# China Pollen Forecast System Frontend

基于 React + TypeScript + Vite 实现的中国全域花粉预报系统演示前端，参考了 `design_china_pollen_forecast_system` 中的 PRD、设计稿与交互方向。

## 已实现内容

- 预报门户大屏
  - 花粉浓度 / 健康风险图层切换
  - `d01` / `d02` 区域切换
  - 未来 72 小时时间轴
  - 重点城市点位和趋势分析
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
  - 导出入口

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

- 当前为高保真业务前端演示版，数据来自本地 mock。
- 暂未接入真实 OpenLayers 地图、Slurm、WPS / WRF / WRF-Pollen 后端接口。
- 下一步建议优先补齐：
  - 后端 API 和认证
  - 工作流运行控制接口
  - 产品清单与发布状态持久化
  - 真实 GIS 底图和栅格/矢量图层渲染
