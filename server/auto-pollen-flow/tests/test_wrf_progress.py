from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.paths import FlowPaths
from lib.wrf_progress import inspect_wrfout_progress, parse_wrfout_time


class WrfProgressTests(unittest.TestCase):
    def test_detects_auto_pollen_archived_wrfout_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            auto_root = root / "auto-pollen"
            output_dir = auto_root / "WRF" / "wrf26052100-26052800" / "output"
            output_dir.mkdir(parents=True)
            wrfout = output_dir / "wrfout_d02_2026-05-24_12-00-00"
            wrfout.write_text("mock wrfout marker\n", encoding="utf-8")

            spec = {
                "run_id": "2026052100_spring_neimeng_official",
                "start": "2026052100",
                "end": "2026052800",
                "nodes": [
                    {
                        "name": "wrf_run",
                        "env": {
                            "AUTO_POLLEN_ROOT": str(auto_root),
                            "WRF_RUN_DIR": str(auto_root / "run"),
                        },
                    }
                ],
            }

            progress = inspect_wrfout_progress(FlowPaths(root / "flow"), spec)

            self.assertTrue(progress["available"], progress)
            self.assertEqual(progress["latest_output_path"], str(wrfout.resolve()))
            self.assertEqual(progress["latest_forecast_time"], "2026-05-24T12:00:00Z")
            self.assertEqual(progress["progress"], 50.0)

    def test_parses_linux_wrfout_time_with_colons(self) -> None:
        self.assertEqual(
            parse_wrfout_time("2026-05-24_12:00:00").isoformat(),
            "2026-05-24T12:00:00+00:00",
        )


if __name__ == "__main__":
    unittest.main()
