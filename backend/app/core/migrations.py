from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from .database import Base
from ..models.models import SchemaMigration

MIGRATIONS = [
    ("20260605_0001_create_metadata", "Create or verify core metadata tables"),
]


def run_migrations(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        for version, description in MIGRATIONS:
            exists = db.query(SchemaMigration).filter(SchemaMigration.version == version).first()
            if exists:
                continue
            db.add(SchemaMigration(version=version, description=description))
        db.commit()
