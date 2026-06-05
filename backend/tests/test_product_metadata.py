from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_password_ssh_uses_sftp_download(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        run_migrations(engine)

        class StubSSH:
            is_local = False
            password = "secret"

            def __init__(self):
                self.downloads = []

            def download_file(self, remote_path, local_path):
                self.downloads.append((remote_path, local_path))

        with Session(engine) as db, mock.patch(
            "backend.app.services.products.sync.subprocess.run",
            side_effect=AssertionError("scp should not be used for password SSH"),
        ):
            ssh = StubSSH()
            service = ProductSyncService(db, ssh=ssh)
            service.download("/remote/product.nc", Path("runtime/products/run/product.nc"))

            self.assertEqual(ssh.downloads, [("/remote/product.nc", Path("runtime/products/run/product.nc"))])


if __name__ == "__main__":
    unittest.main()
