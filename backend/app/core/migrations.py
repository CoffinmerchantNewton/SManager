from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session

from .database import Base
from ..models.models import SchemaMigration

MIGRATIONS = [
    ("20260605_0001_create_metadata", "Create or verify core metadata tables"),
    ("20260605_0002_product_manifest_metadata", "Add product manifest metadata columns"),
    ("20260605_0003_run_node_wrfout_progress", "Add WRF output progress metadata to run nodes"),
]

PRODUCT_METADATA_COLUMNS = {
    "subtype": "VARCHAR",
    "variable": "VARCHAR",
    "unit": "VARCHAR",
    "bounds_json": "TEXT",
    "lead_time": "VARCHAR",
    "source_run_id": "VARCHAR",
    "capability_status": "VARCHAR",
}

RUN_NODE_WRFOUT_COLUMNS = {
    "wrfout_progress_json": "TEXT",
}


def run_migrations(engine: Engine) -> None:
    with migration_lock(engine):
        Base.metadata.create_all(bind=engine)
        for version, description in MIGRATIONS:
            if migration_exists(engine, version):
                continue
            if version == "20260605_0002_product_manifest_metadata":
                add_missing_columns(engine, "forecast_products", PRODUCT_METADATA_COLUMNS)
            elif version == "20260605_0003_run_node_wrfout_progress":
                add_missing_columns(engine, "forecast_run_nodes", RUN_NODE_WRFOUT_COLUMNS)
            with Session(engine) as db:
                db.add(SchemaMigration(version=version, description=description))
                db.commit()


def migration_exists(engine: Engine, version: str) -> bool:
    with Session(engine) as db:
        return db.query(SchemaMigration).filter(SchemaMigration.version == version).first() is not None


def add_missing_columns(engine: Engine, table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    missing = [(name, ddl) for name, ddl in columns.items() if name not in existing]
    if not missing:
        return
    with engine.begin() as connection:
        for name, ddl in missing:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}"))


@contextmanager
def migration_lock(engine: Engine):
    lock_path = sqlite_lock_path(engine)
    if lock_path is None:
        yield
        return
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = acquire_lock_file(lock_path)
    try:
        yield
    finally:
        os.close(handle)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def sqlite_lock_path(engine: Engine) -> Path | None:
    if engine.url.get_backend_name() != "sqlite":
        return None
    database = engine.url.database
    if not database or database == ":memory:":
        return None
    return Path(database).resolve().with_suffix(".migration.lock")


def acquire_lock_file(lock_path: Path, timeout_seconds: float = 30, poll_seconds: float = 0.1) -> int:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            return os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for migration lock: {lock_path}") from None
            time.sleep(poll_seconds)
