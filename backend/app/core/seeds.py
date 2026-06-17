from __future__ import annotations

from sqlalchemy.orm import Session


def seed_operational_defaults(db: Session) -> None:
    """Reserved for future local-only defaults. Server-owned runs no longer seed workflows here."""
    del db
