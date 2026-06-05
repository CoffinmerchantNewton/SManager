from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.core.migrations import run_migrations
from backend.app.models.models import ForecastProduct
from backend.app.services.products.sync import ProductSyncService


class ProductMetadataSyncTest(unittest.TestCase):
    def test_manifest_metadata_is_persisted(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        run_migrations(engine)

        with tempfile.TemporaryDirectory() as tmp, Session(engine) as db:
            local_path = Path(tmp) / "contour.geojson"
            item = {
                "name": "contour.geojson",
                "type": "geojson",
                "subtype": "contour",
                "variable": "pollen_total",
                "unit": "grains/kg-dryair",
                "bounds": {"west": 70, "south": 15, "east": 140, "north": 55},
                "lead_time": "P1D",
                "source_run_id": "2026060400_spring_neimeng_official",
                "capability_status": "generated",
            }

            product = ProductSyncService(db).upsert_product("run-a", item, "contour.geojson", local_path)
            saved = db.query(ForecastProduct).filter(ForecastProduct.id == product.id).one()

            self.assertEqual(saved.subtype, "contour")
            self.assertEqual(saved.variable, "pollen_total")
            self.assertEqual(saved.unit, "grains/kg-dryair")
            self.assertIn('"west": 70', saved.bounds_json or "")
            self.assertEqual(saved.lead_time, "P1D")
            self.assertEqual(saved.source_run_id, "2026060400_spring_neimeng_official")
            self.assertEqual(saved.capability_status, "generated")


if __name__ == "__main__":
    unittest.main()
