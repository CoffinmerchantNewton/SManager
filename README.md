# China Pollen Forecast System

基于 WRF-Pollen / WRF-Chem 的全国花粉扩散与业务预报平台

## 项目结构

```
SManager/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # Pydantic 模式
│   │   ├── init_db.py      # 数据库初始化
│   │   └── main.py         # 应用入口
│   ├── requirements.txt
│   ├── run.py
│   └── README.md
│
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/    # 可复用组件
│   │   ├── pages/         # 页面组件
│   │   ├── services/      # API 服务
│   │   ├── types/         # TypeScript 类型
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── README.md
│
└── design_china_pollen_forecast_system/  # 设计文件
    ├── prd.md
    └── meteorological_precision_system/
        └── DESIGN.md
```

## 快速开始

### 后端启动

```bash
cd backend
pip install -r requirements.txt
python run.py
```

后端将在 http://localhost:8000 启动

API 文档: http://localhost:8000/docs

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端将在 http://localhost:3000 启动

## 功能特性

### 1. 预报门户 (Portal)
- WebGIS 地图展示
- 实时花粉浓度监控
- 时间序列分析

### 2. 管理员控制台
- **Dashboard**: 系统概览和实时监控
- **Workflow Editor**: 工作流 DAG 可视化编排
- **Task Scheduler**: 定时任务管理
- **Products Management**: 预报产品管理

### 3. 后端 API
- RESTful API 设计
- SQLite 数据库
- 自动生成示例数据
- 完整的 CRUD 操作

## 技术栈

### 后端
- **FastAPI**: 现代 Python Web 框架
- **SQLAlchemy**: ORM
- **SQLite**: 数据库
- **Pydantic**: 数据验证

### 前端
- **React 19**: UI 框架
- **TypeScript**: 类型安全
- **React Router**: 路由管理
- **Axios**: HTTP 客户端
- **Tailwind CSS**: 样式框架
- **Vite**: 构建工具

## 设计系统

基于 NASA 气象业务系统风格:
- **深色主题**: #121414 背景
- **科技蓝/青色**: 高亮和交互元素
- **字体**: Inter (正文) + Space Grotesk (数据/标签)
- **圆角**: 4px-8px 软方形几何
- **间距**: 4px 基准网格

## 默认登录

- **密码**: `admin123`

## API 端点

### Workflows
- `GET /api/v1/workflows` - 获取所有工作流
- `GET /api/v1/workflows/{id}` - 获取工作流详情
- `GET /api/v1/workflows/{id}/nodes` - 获取工作流节点

### Tasks
- `GET /api/v1/tasks` - 获取所有定时任务
- `PATCH /api/v1/tasks/{id}/status` - 更新任务状态

### Products
- `GET /api/v1/products` - 获取预报产品列表
- `PATCH /api/v1/products/{id}/publish` - 切换发布状态
- `DELETE /api/v1/products/{id}` - 删除产品

### Dashboard
- `GET /api/v1/dashboard/stats` - 获取仪表板统计
- `GET /api/v1/dashboard/logs` - 获取系统日志

## 开发说明

### 数据库初始化

首次运行时，`run.py` 会自动初始化数据库并填充示例数据。

### 环境变量

前端 `.env` 文件:
```
VITE_API_URL=http://localhost:8000/api/v1
```

后端配置在 `backend/app/core/config.py`

## 参考资料

- PRD: `design_china_pollen_forecast_system/prd.md`
- 设计系统: `design_china_pollen_forecast_system/meteorological_precision_system/DESIGN.md`
- ecFlow 参考: `reference/ecflow/`

## License

MIT
