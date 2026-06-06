from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.preflight import run_preflight
from lib.slurm import submit_sbatch


class PreflightTests(unittest.TestCase):
    def test_preflight_accepts_configured_nodes_and_fnl_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            node_dir = root / "node_commands"
            auto_root = root / "auto-pollen"
            fnl_root = root / "fnl"
            node_dir.mkdir()
            auto_root.mkdir()
            fnl_root.mkdir()

            config = {
                "env": {
                    "NODE_COMMAND_DIR": str(node_dir),
                    "AUTO_POLLEN_ROOT": str(auto_root),
                },
                "slurm_defaults": {
                    "partition": "normal",
                    "nodes": 1,
                    "ntasks": 1,
                    "cpus_per_task": 4,
                },
                "nodes": {
                    name: {
                        "command": f"bash {node_dir / (name + '.sh')}",
                        "env": {env_name: "true"},
                    }
                    for name, env_name in {
                        "wps_geogrid": "WPS_GEOGRID_COMMAND",
                        "wps_ungrib": "WPS_UNGRIB_COMMAND",
                        "wps_metgrid": "WPS_METGRID_COMMAND",
                        "wrf_setup": "WRF_SETUP_COMMAND",
                        "real": "REAL_COMMAND",
                        "compute_gdd": "COMPUTE_GDD_COMMAND",
                        "prep_pollen": "PREP_POLLEN_COMMAND",
                        "wrf_run": "WRF_RUN_COMMAND",
                        "postprocess_eval": "POSTPROCESS_EVAL_COMMAND",
                    }.items()
                },
            }

            with (
                mock.patch.dict(os.environ, {"FNL_ROOT": str(fnl_root)}, clear=False),
                mock.patch("lib.preflight.shutil.which", side_effect=lambda command: command if command == "bash" else None),
            ):
                result = run_preflight(root, config)

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["summary"]["failed_required"], 0)

    def test_preflight_reports_missing_required_node_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fnl_root = root / "fnl"
            fnl_root.mkdir()

            config = {
                "slurm_defaults": {
                    "partition": "normal",
                    "nodes": 1,
                    "ntasks": 1,
                    "cpus_per_task": 4,
                },
                "nodes": {},
            }

            with (
                mock.patch.dict(os.environ, {"FNL_ROOT": str(fnl_root)}, clear=False),
                mock.patch("lib.preflight.shutil.which", side_effect=lambda command: command if command == "bash" else None),
            ):
                result = run_preflight(root, config)

            self.assertFalse(result["ok"])
            failed = [item["name"] for item in result["checks"] if not item["ok"] and item.get("required", True)]
            self.assertIn("node:wps_geogrid", failed)

    def test_preflight_accepts_custom_node_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fnl_root = root / "fnl"
            fnl_root.mkdir()

            config = {
                "env": {"FNL_ROOT": str(fnl_root)},
                "node_order": ["prepare_temperature", "generate_wrfchemi", "wrf_run"],
                "slurm_defaults": {
                    "partition": "normal",
                    "nodes": 1,
                    "ntasks": 1,
                    "cpus_per_task": 1,
                },
                "nodes": {
                    "prepare_temperature": {"command": "true"},
                    "generate_wrfchemi": {"command": "true"},
                    "wrf_run": {"command": "true", "env": {"WRF_RUN_COMMAND": "true"}},
                },
            }

            with mock.patch("lib.preflight.shutil.which", side_effect=lambda command: command if command == "bash" else None):
                result = run_preflight(root, config)

            self.assertTrue(result["ok"], result)
            checked_nodes = [item["node"] for item in result["checks"] if item["name"].startswith("node:")]
            self.assertEqual(checked_nodes, ["prepare_temperature", "generate_wrfchemi", "wrf_run"])


class SlurmMockTests(unittest.TestCase):
    def test_submit_sbatch_parses_job_id_from_mock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sbatch = write_mock_sbatch(root, "12345.mock", exit_code=0)
            script = root / "job.sbatch"
            script.write_text("#!/bin/sh\ntrue\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {"PATH": f"{root}{os.pathsep}{os.environ.get('PATH', '')}"}):
                self.assertEqual(submit_sbatch(script), "12345.mock")

    def test_submit_sbatch_raises_on_failed_mock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sbatch = write_mock_sbatch(root, "queue closed", exit_code=2)
            script = root / "job.sbatch"
            script.write_text("#!/bin/sh\ntrue\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {"PATH": f"{root}{os.pathsep}{os.environ.get('PATH', '')}"}):
                with self.assertRaisesRegex(RuntimeError, "queue closed"):
                    submit_sbatch(script)


def write_mock_sbatch(root: Path, output: str, exit_code: int) -> Path:
    if os.name == "nt":
        path = root / "sbatch.bat"
        path.write_text(f"@echo off\necho {output}\nexit /b {exit_code}\n", encoding="utf-8")
    else:
        path = root / "sbatch"
        path.write_text(f"#!/bin/sh\necho {output}\nexit {exit_code}\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


if __name__ == "__main__":
    unittest.main()
