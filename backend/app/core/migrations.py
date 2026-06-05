from __future__ import annotations

from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session

from .database import Base
from ..models.models import SchemaMigration

MIGRATIONS = [
    ("20260605_0001_create_metadata", "Create or verify core metadata tables"),
    ("20260605_0002_product_manifest_metadata", "Add product manifest metadata columns"),
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


def run_migrations(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        for version, description in MIGRATIONS:
            exists = db.query(SchemaMigration).filter(SchemaMigration.version == version).first()
            if exists:
                continue
            if version == "20260605_0002_product_manifest_metadata":
                add_missing_columns(engine, "forecast_products", PRODUCT_METADATA_COLUMNS)
            db.add(SchemaMigration(version=version, description=description))
        db.commit()


def add_missing_columns(engine: Engine, table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    missing = [(name, ddl) for name, ddl in columns.items() if name not in existing]
    if not missing:
        return
    with engine.begin() as connection:
        for name, ddl in missing:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}"))
