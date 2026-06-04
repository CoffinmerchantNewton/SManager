# China Pollen Forecast System - Backend

FastAPI backend for the China Pollen Forecast System.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python run.py
```

The API will be available at http://localhost:8000

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Workflows
- `GET /api/v1/workflows` - List all workflows
- `GET /api/v1/workflows/{id}` - Get workflow details
- `POST /api/v1/workflows` - Create new workflow
- `GET /api/v1/workflows/{id}/nodes` - Get workflow nodes
- `PATCH /api/v1/workflows/{id}/status` - Update workflow status

### Tasks
- `GET /api/v1/tasks` - List scheduled tasks
- `GET /api/v1/tasks/{id}` - Get task details
- `POST /api/v1/tasks` - Create new task
- `PATCH /api/v1/tasks/{id}/status` - Update task status
- `DELETE /api/v1/tasks/{id}` - Delete task

### Products
- `GET /api/v1/products` - List forecast products (with filters)
- `GET /api/v1/products/{id}` - Get product details
- `GET /api/v1/products/{id}/download` - Download synced product file
- `POST /api/v1/products` - Create new product
- `PATCH /api/v1/products/{id}/publish` - Toggle publish status
- `DELETE /api/v1/products/{id}` - Delete product

### Dashboard
- `GET /api/v1/dashboard/stats` - Get dashboard statistics
- `GET /api/v1/dashboard/logs` - Get system logs
