import unittest

from packages.diagnostics import analyze_diagnosis


class DiagnosticsAnalysisTest(unittest.TestCase):
    def test_fnl_findings_allow_repair_action(self):
        result = analyze_diagnosis(
            {
                "run_id": "run_a",
                "status": "error",
                "findings": [{"node": "fnl_verify", "code": "fnl_missing"}],
            }
        )

        self.assertTrue(result["summary"]["auto_retry_allowed"])
        self.assertFalse(result["summary"]["requires_operator"])
        self.assertEqual(result["summary"]["recommended_next_action"], "repair_fnl")
        self.assertEqual(
            result["recommendations"][0]["cli"],
            "python3 packages/cli/smanager.py fnl-repair --run-id run_a",
        )

    def test_infrastructure_findings_block_auto_retry(self):
        result = analyze_diagnosis(
            {
                "run_id": "run_b",
                "status": "error",
                "findings": [
                    {"node": "wps_ungrib", "code": "fnl_missing"},
                    {"node": "wrf_run", "code": "disk_full"},
                ],
            }
        )

        self.assertFalse(result["summary"]["auto_retry_allowed"])
        self.assertTrue(result["summary"]["requires_operator"])
        self.assertEqual(result["summary"]["risk_level"], "critical")
        self.assertEqual(result["summary"]["recommended_next_action"], "notify_operator")


if __name__ == "__main__":
    unittest.main()
