from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import product_extract


class ProductMetadataTests(unittest.TestCase):
    def test_capability_status_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            source = output_dir / "summary.nc"
            source.write_text("placeholder", encoding="utf-8")
            path = product_extract.write_capability_status(
                output_dir,
                source,
                "pollen_total",
                "geotiff",
                "skipped",
                ModuleNotFoundError("rasterio"),
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["type"], "capability_status")
        self.assertEqual(payload["capability"], "geotiff")
        self.assertEqual(payload["status"], "skipped")
        self.assertEqual(payload["variable"], "pollen_total")

    def test_station_config_has_valid_city_points(self) -> None:
        path = ROOT / "templates" / "run_spec" / "stations.china_pollen.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        cities = product_extract.normalize_city_points(payload)

        self.assertGreaterEqual(len(cities), 20)
        self.assertTrue(all("name" in city and "longitude" in city and "latitude" in city for city in cities))


if __name__ == "__main__":
    unittest.main()
