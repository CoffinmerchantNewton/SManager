import json
import unittest
from pathlib import Path


CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "packages" / "contracts"


class ContractsTest(unittest.TestCase):
    def test_contract_files_parse(self):
        for path in CONTRACTS_DIR.glob("*.schema.json"):
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertIn("$id", payload)
                self.assertIn("title", payload)

    def test_required_contracts_exist(self):
        expected = {
            "agent_action.schema.json",
            "diagnosis_analysis.schema.json",
            "fnl_manifest.schema.json",
            "node_status.schema.json",
            "product_manifest.schema.json",
            "run_spec.schema.json",
            "workflow_status.schema.json",
        }
        existing = {path.name for path in CONTRACTS_DIR.glob("*.schema.json")}
        self.assertTrue(expected.issubset(existing))

    def test_workflow_status_contract_has_nodes(self):
        payload = json.loads((CONTRACTS_DIR / "workflow_status.schema.json").read_text(encoding="utf-8"))
        self.assertIn("nodes", payload["required"])
        self.assertEqual(payload["properties"]["nodes"]["items"]["$ref"], "node_status.schema.json")


if __name__ == "__main__":
    unittest.main()
