from __future__ import annotations

import os
from pathlib import Path


class FlowPaths:
    def __init__(self, root: Path):
        self.root = root.resolve()

    @classmethod
    def from_env(cls, script_dir: Path) -> "FlowPaths":
        root = os.environ.get("AUTO_POLLEN_FLOW_ROOT")
        return cls(Path(root) if root else script_dir)

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    def run_dir(self, run_id: str) -> Path:
        return self.runs_dir / run_id

    def state_dir(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "state"

    def logs_dir(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "logs"

    def slurm_dir(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "slurm"

    def products_dir(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "products"

    def run_spec(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "run_spec.json"

    def workflow_status(self, run_id: str) -> Path:
        return self.state_dir(run_id) / "workflow.status.json"

    def node_status(self, run_id: str, node: str) -> Path:
        return self.state_dir(run_id) / f"{node}.status.json"

    def events(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "events.jsonl"

    def fnl_manifest(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "fnl_manifest.json"

    def product_manifest(self, run_id: str) -> Path:
        return self.products_dir(run_id) / "product_manifest.json"
