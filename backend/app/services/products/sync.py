from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ...core.config import settings
from ...models.models import ForecastProduct, ProductStatus
from ..audit import create_action, finish_action
from ..flow import ServerFlowService
from ..ssh import SSHClient


class ProductSyncService:
    def __init__(
        self,
        db: Session,
        flow: ServerFlowService | None = None,
        ssh: SSHClient | None = None,
    ):
        self.db = db
        self.flow = flow or ServerFlowService()
        self.ssh = ssh or SSHClient()

    def sync(self, run_id: str) -> dict[str, Any]:
        action = create_action(
            self.db,
            action_type="product_sync",
            status="running",
            run_id=run_id,
            reason="sync server product manifest to jumpbox",
        )
        try:
            manifest = self.flow.products(run_id)
            workflow = self.flow.status(run_id)
            remote_product_dir = self.remote_product_dir(workflow)
            synced = []
            for item in manifest.get("products", []):
                synced.append(self.sync_one(run_id, item, remote_product_dir))
            output = {"ok": all(item.get("ok") for item in synced), "run_id": run_id, "products": synced}
            finish_action(self.db, action, "success" if output["ok"] else "error", output)
            return output
        except Exception as exc:
            output = {"ok": False, "error": exc.__class__.__name__, "message": str(exc)}
            finish_action(self.db, action, "error", output)
            return output

    def sync_one(self, run_id: str, item: dict[str, Any], remote_product_dir: str | None) -> dict[str, Any]:
        name = item.get("name") or Path(item.get("path", "product")).name
        remote_path = self.resolve_remote_path(item, remote_product_dir)
        local_path = Path(settings.JUMPBOX_PRODUCTS_DIR) / run_id / name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.download(remote_path, local_path)
            product = self.upsert_product(run_id, item, name, local_path)
            return {
                "ok": True,
                "name": name,
                "remote_path": remote_path,
                "local_path": str(local_path),
                "product_id": product.id,
            }
        except Exception as exc:
            return {
                "ok": False,
                "name": name,
                "remote_path": remote_path,
                "error": exc.__class__.__name__,
                "message": str(exc),
            }

    def resolve_remote_path(self, item: dict[str, Any], remote_product_dir: str | None) -> str:
        path = item.get("server_path") or item.get("path")
        if not path:
            raise ValueError("product item requires path or server_path")
        if str(path).startswith("/"):
            return str(path)
        if not remote_product_dir:
            raise ValueError(f"relative product path cannot be resolved: {path}")
        return f"{remote_product_dir.rstrip('/')}/{path}"

    def remote_product_dir(self, workflow: dict[str, Any]) -> str | None:
        run_spec_path = workflow.get("run_spec_path")
        if not run_spec_path:
            return None
        return str(Path(run_spec_path).parent / "products")

    def download(self, remote_path: str, local_path: Path) -> None:
        if self.ssh.is_local:
            shutil.copy2(remote_path, local_path)
            return
        method = settings.PRODUCT_SYNC_METHOD.lower()
        if method == "rsync" and shutil.which("rsync"):
            self.run_rsync(remote_path, local_path)
        else:
            self.run_scp(remote_path, local_path)

    def run_rsync(self, remote_path: str, local_path: Path) -> None:
        source = self.remote_target(remote_path)
        ssh_cmd = f"ssh -p {settings.SERVER_SSH_PORT}"
        result = subprocess.run(
            ["rsync", "-av", "--partial", "-e", ssh_cmd, source, str(local_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"rsync download failed: {result.stdout.strip()}")

    def run_scp(self, remote_path: str, local_path: Path) -> None:
        source = self.remote_target(remote_path)
        result = subprocess.run(
            ["scp", "-P", str(settings.SERVER_SSH_PORT), source, str(local_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"scp download failed: {result.stdout.strip()}")

    def remote_target(self, remote_path: str) -> str:
        host = settings.SERVER_SSH_HOST
        if not host:
            raise RuntimeError("SERVER_SSH_HOST is not configured for remote product sync")
        user_host = f"{settings.SERVER_SSH_USER}@{host}" if settings.SERVER_SSH_USER else host
        return f"{user_host}:{remote_path}"

    def upsert_product(self, run_id: str, item: dict[str, Any], name: str, local_path: Path) -> ForecastProduct:
        product_name = f"{run_id}:{name}"
        product = self.db.query(ForecastProduct).filter(ForecastProduct.product_name == product_name).first()
        if not product:
            product = ForecastProduct(product_name=product_name)
            self.db.add(product)
        product.product_type = item.get("type") or item.get("product_type") or "artifact"
        product.status = ProductStatus.READY
        product.region = item.get("region") or "unknown"
        product.pollen_type = item.get("pollen_type") or "unknown"
        product.resolution = item.get("resolution") or "unknown"
        product.workflow_node = item.get("workflow_node") or "package_products"
        product.workflow_version = item.get("workflow_version") or run_id
        product.file_path = str(local_path)
        product.thumbnail_path = item.get("thumbnail_path")
        self.db.commit()
        self.db.refresh(product)
        return product
