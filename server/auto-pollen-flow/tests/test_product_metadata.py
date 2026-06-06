from __future__ import annotations

import json
import os
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

    def test_reduce_to_2d_defaults_to_strongest_time_slice(self) -> None:
        try:
            import numpy as np  # type: ignore
        except ModuleNotFoundError:
            self.skipTest("numpy is not installed")
        previous = os.environ.pop("PRODUCT_TIME_INDEX", None)
        try:
            data = np.array(
                [
                    [[0.0, 0.0], [0.0, 0.0]],
                    [[1.0, 2.0], [3.0, 4.0]],
                    [[0.5, 0.0], [0.0, 0.0]],
                ]
            )
            reduced = product_extract.reduce_to_2d(data)
        finally:
            if previous is not None:
                os.environ["PRODUCT_TIME_INDEX"] = previous

        self.assertEqual(float(reduced.max()), 4.0)

    def test_pollen_png_defaults_to_log_scale(self) -> None:
        self.assertEqual(
            product_extract.png_color_scale("pollen_total", {"min": 0.0, "max": 56000.0}),
            "log1p",
        )
        legend = product_extract.color_legend(0.0, 56000.0, "log1p")
        self.assertLess(legend[1]["value"], 56000.0 * 0.35)


if __name__ == "__main__":
    unittest.main()
