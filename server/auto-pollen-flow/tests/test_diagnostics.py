from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.diagnostics import diagnose
from lib.jsonio import write_json_atomic
from lib.paths import FlowPaths


class DiagnosticsTests(unittest.TestCase):
    def test_successful_node_ignores_stale_log_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._paths(tmp)
            run_id = "run_success"
            self._write_workflow(paths, run_id, "wps_geogrid", "success")
            (paths.logs_dir(run_id) / "wps_geogrid.log").write_text(
                "Batch job submission failed once before retry\nnode command completed\n",
                encoding="utf-8",
            )

            result = diagnose(paths, run_id)

            self.assertEqual([], result["findings"])

    def test_error_node_keeps_log_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._paths(tmp)
            run_id = "run_error"
            self._write_workflow(paths, run_id, "wps_geogrid", "error", error_code="slurm_submit_failed")
            (paths.logs_dir(run_id) / "wps_geogrid.log").write_text(
                "sbatch: Batch job submission failed\n",
                encoding="utf-8",
            )

            result = diagnose(paths, run_id)

            codes = [item["code"] for item in result["findings"]]
            self.assertIn("slurm_submit_failed", codes)

    def _paths(self, root: str) -> FlowPaths:
        paths = FlowPaths(Path(root))
        paths.runs_dir.mkdir(parents=True, exist_ok=True)
        return paths

    def _write_workflow(
        self,
        paths: FlowPaths,
        run_id: str,
        node: str,
        status: str,
        error_code: str | None = None,
    ) -> None:
        paths.state_dir(run_id).mkdir(parents=True, exist_ok=True)
        paths.logs_dir(run_id).mkdir(parents=True, exist_ok=True)
        write_json_atomic(
            paths.workflow_status(run_id),
            {
                "run_id": run_id,
                "status": "success" if status == "success" else "error",
                "nodes": [
                    {
                        "node": node,
                        "status": status,
                        "error_code": error_code,
                        "message": "node command completed" if status == "success" else "failed",
                    }
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
