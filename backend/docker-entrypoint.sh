#!/bin/sh
set -e

echo "Waiting for MySQL..."
python - <<'PY'
import os
import sys
import time
from urllib.parse import unquote, urlparse

import pymysql

database_url = os.environ.get("DATABASE_URL", "")
if not database_url.startswith("mysql+pymysql://"):
    print("DATABASE_URL missing or invalid; skip wait")
    sys.exit(0)

parsed = urlparse(database_url.replace("mysql+pymysql://", "mysql://", 1))
user = unquote(parsed.username or "")
password = unquote(parsed.password or "")
host = parsed.hostname or "mysql"
port = parsed.port or 3306
database = (parsed.path or "/smanager").lstrip("/").split("?", 1)[0]

for attempt in range(1, 61):
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
            connect_timeout=3,
        )
        conn.close()
        print("MySQL is ready")
        break
    except Exception as exc:
        if attempt == 60:
            print(f"MySQL not ready after 120s: {exc}")
            sys.exit(1)
        time.sleep(2)
PY

echo "Starting FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
