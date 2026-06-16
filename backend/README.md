# SManager Local Backend

FastAPI backend for the local monitoring and FNL supply side of SManager.

The backend is no longer the primary forecast scheduler. Daily forecast scheduling, Slurm submission, FNL fallback, and recovery will live in the future `smanager-server` daemon on the CentOS server.

## Setup

```bash
pip install -r requirements.txt
cp backend/.env.example backend/.env
python run.py
```

The backend reads `.env` from the repository root and `backend/.env`.

## Database

Use MySQL only:

```bash
DATABASE_URL="mysql+pymysql://smanager:12345678@127.0.0.1:3306/smanager?charset=utf8mb4"
```

SQLite runtime files and SQLite tests have been removed.

## Current Role

- Store local status snapshots and product/FNL metadata in MySQL.
- Serve the local frontend.
- Expose storage and health checks.
- Keep placeholder API responses for run/FNL actions until the new tunnel and server daemon are implemented.

## Current Boundaries

- No direct SSH/Paramiko controller.
- No local scheduler as the source of truth.
- No old `packages/`, `scripts/`, or `server/auto-*` dependencies.
