from __future__ import annotations

from typing import Any

from packages.diagnostics import analyze_diagnosis


def enrich_diagnosis(diagnosis: dict[str, Any], run_id: str | None = None) -> dict[str, Any]:
    enriched = dict(diagnosis)
    enriched["analysis"] = analyze_diagnosis(enriched, run_id=run_id)
    return enriched
