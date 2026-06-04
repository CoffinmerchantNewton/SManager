# China Pollen Forecast System - Backend

FastAPI backend for the China Pollen Forecast System.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a local environment file:
```bash
cp backend/.env.example backend/.env
```

The backend reads `.env` from the repository root and `backend/.env`. Use `SERVER_SSH_HOST=local` for local smoke tests where `flowctl` runs on the same machine. For the jumpbox deployment, set `SERVER_SSH_HOST`, `SERVER_SSH_USER`, `SERVER_FLOWCTL_PATH`, `SERVER_FLOW_ROOT`, `SERVER_FNL_ROOTS`, and `SERVER_FNL_UPLOAD_DIR` for the CentOS server.

FNL repair uses `FNL_DOWNLOAD_COMMAND` only after server-side verification reports missing or invalid files. The command receives `FNL_VALID_TIME`, `FNL_FILE_NAME`, and `FNL_OUTPUT_PATH`, and must write a GRIB2 file to `FNL_OUTPUT_PATH`.

For local smoke tests, you can set:
```bash
FNL_DOWNLOAD_COMMAND="python3 scripts/fake_fnl_download.py"
FNL_FAKE_SIZE_MB=6
```

This writes a synthetic file beginning with `GRIB` and is only intended to test the repair/upload/control loop.

3. Run the application:
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

### Run Control
- `GET /api/v1/runs/{run_id}/status` - Read server workflow status
- `GET /api/v1/runs/{run_id}/diagnose` - Read server diagnostics
- `POST /api/v1/runs/{run_id}/retry` - Retry one node
- `POST /api/v1/runs/{run_id}/cancel` - Cancel active run nodes
- `GET /api/v1/runs/{run_id}/logs` - Read run or node logs
- `POST /api/v1/runs/{run_id}/sync-products` - Sync and index run products

### Dashboard
- `GET /api/v1/dashboard/stats` - Get dashboard statistics
- `GET /api/v1/dashboard/logs` - Get system logs

Dashboard stats are sourced from `forecast_runs` and `forecast_run_nodes`: run counts come from `forecast_runs`, active Slurm node count comes from nodes with `slurm_job_id`, and system health is derived from recent run failures and active run pressure.
