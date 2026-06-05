# MySQL Runbook

本文记录本机 `D:\Mysql` 的 SManager MySQL 初始化、启动和 SQLite 迁移方式。

## Paths

- MySQL root: `D:\Mysql`
- Config: `D:\Mysql\my.ini`
- Data: `D:\Mysql\data`
- DDL baseline: `backend/ddl/mysql.sql`
- Migration helper: `scripts/migrate_sqlite_to_mysql.py`

## Local Credentials

- MySQL `root` password: `12345678`
- App database: `smanager`
- App user: `smanager`
- App user password: `12345678`

Do not commit `.env`; the repository only keeps examples and DDL.

## Initialize

Only run initialization when `D:\Mysql\data` does not exist.

```powershell
@'
[mysqld]
basedir=D:/Mysql
datadir=D:/Mysql/data
port=3306
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
default-time-zone=+08:00
sql-mode=STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION

[client]
default-character-set=utf8mb4
port=3306
'@ | Set-Content -Encoding ASCII D:\Mysql\my.ini

D:\Mysql\bin\mysqld.exe --defaults-file=D:\Mysql\my.ini --initialize-insecure --console
```

Start MySQL for local development:

```powershell
Start-Process -FilePath D:\Mysql\bin\mysqld.exe `
  -ArgumentList "--defaults-file=D:\Mysql\my.ini" `
  -WorkingDirectory D:\Mysql `
  -WindowStyle Hidden
```

Set password, database and user:

```powershell
D:\Mysql\bin\mysql.exe --protocol=tcp --host=127.0.0.1 --port=3306 --user=root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '12345678'; CREATE DATABASE IF NOT EXISTS smanager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS 'smanager'@'localhost' IDENTIFIED BY '12345678'; ALTER USER 'smanager'@'localhost' IDENTIFIED BY '12345678'; GRANT ALL PRIVILEGES ON smanager.* TO 'smanager'@'localhost'; FLUSH PRIVILEGES;"
```

## Migrate SQLite To MySQL

Install the Python driver in the backend environment:

```powershell
conda run --no-capture-output -n smanager python -m pip install PyMySQL==1.1.1
```

Run the migration:

```powershell
$mysqlUrl = "mysql+pymysql://smanager:12345678@127.0.0.1:3306/smanager?charset=utf8mb4"
conda run --no-capture-output -n smanager python scripts/migrate_sqlite_to_mysql.py `
  --mysql-url $mysqlUrl `
  --truncate
```

Set local `.env`:

```env
DATABASE_URL="mysql+pymysql://smanager:12345678@127.0.0.1:3306/smanager?charset=utf8mb4"
```

## Verify

```powershell
D:\Mysql\bin\mysql.exe --protocol=tcp --host=127.0.0.1 --port=3306 --user=smanager --password=12345678 smanager -e "SHOW TABLES; SELECT COUNT(*) FROM forecast_runs;"

@'
import backend.app.main
from backend.app.core.database import SessionLocal
from backend.app.models.models import ForecastRun
with SessionLocal() as db:
    print(db.query(ForecastRun).count())
'@ | conda run --no-capture-output -n smanager python -
```

## Notes

`SManagerMySQL` was registered with `mysqld --install`, but this machine reported Windows service error 1053 during service start. The service is therefore left as `Manual` to avoid boot-time errors. The database runs correctly as a hidden `mysqld.exe` process with the same `my.ini`; service startup can be revisited separately if automatic boot startup is required.
