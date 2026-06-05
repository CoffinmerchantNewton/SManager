from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy import MetaData, create_engine, delete, select
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.migrations import run_migrations
from backend.app.models.models import Base


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate SManager metadata from SQLite to MySQL.")
    parser.add_argument("--sqlite-url", default="sqlite:///./runtime/db/pollen_forecast.sqlite")
    parser.add_argument("--mysql-url", required=True)
    parser.add_argument("--truncate", action="store_true", help="Delete target rows before loading.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sqlite_engine = create_engine(args.sqlite_url, connect_args={"check_same_thread": False})
    mysql_engine = create_engine(args.mysql_url, pool_pre_ping=True)

    run_migrations(mysql_engine)
    if args.truncate:
        truncate_tables(mysql_engine, reversed(Base.metadata.sorted_tables))
    copied = copy_tables(sqlite_engine, mysql_engine, Base.metadata.sorted_tables)
    for table_name, count in copied:
        print(f"{table_name}: {count}")
    return 0


def truncate_tables(engine: Engine, tables: Iterable) -> None:
    with engine.begin() as connection:
        connection.execute(delete(Base.metadata.tables["schema_migrations"]))
        for table in tables:
            if table.name == "schema_migrations":
                continue
            connection.execute(delete(table))


def copy_tables(source_engine: Engine, target_engine: Engine, tables: Iterable) -> list[tuple[str, int]]:
    source_meta = MetaData()
    source_meta.reflect(bind=source_engine)
    result: list[tuple[str, int]] = []
    with source_engine.connect() as source, target_engine.begin() as target:
        for target_table in tables:
            source_table = source_meta.tables.get(target_table.name)
            if source_table is None:
                result.append((target_table.name, 0))
                continue
            rows = [dict(row._mapping) for row in source.execute(select(source_table)).all()]
            if rows:
                target.execute(target_table.insert(), rows)
            result.append((target_table.name, len(rows)))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
