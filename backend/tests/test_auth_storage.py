from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path
from unittest import mock

from backend.app.core import security
from backend.app.core.config import settings
from backend.app.services.storage import StorageService


class AuthSecurityTest(unittest.TestCase):
    def test_admin_token_round_trip(self):
        old_user = settings.ADMIN_USERNAME
        old_password = settings.ADMIN_PASSWORD
        old_secret = settings.SECRET_KEY
        try:
            settings.ADMIN_USERNAME = "operator"
            settings.ADMIN_PASSWORD = "secret"
            settings.SECRET_KEY = "unit-test-secret"
            self.assertTrue(security.verify_admin_credentials("operator", "secret"))
            self.assertFalse(security.verify_admin_credentials("operator", "wrong"))
            token = security.create_access_token("operator")
            payload = security.decode_access_token(token)
            self.assertEqual(payload["sub"], "operator")
        finally:
            settings.ADMIN_USERNAME = old_user
            settings.ADMIN_PASSWORD = old_password
            settings.SECRET_KEY = old_secret


class StorageCleanupTest(unittest.TestCase):
    def test_cleanup_dry_run_selects_old_files_without_deleting_gitkeep(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_file = root / "old.dat"
            gitkeep = root / ".gitkeep"
            old_file.write_text("payload", encoding="utf-8")
            gitkeep.write_text("", encoding="utf-8")
            os.utime(old_file, (1, 1))

            with mock.patch("backend.app.services.storage.storage_roots", return_value={"cache": str(root)}):
                result = StorageService().cleanup(dry_run=True, retention_days=0, max_gb=100)

            self.assertTrue(result["ok"])
            self.assertEqual(result["selected_count"], 1)
            self.assertEqual(result["deleted_count"], 0)
            self.assertTrue(old_file.exists())
            self.assertTrue(gitkeep.exists())


if __name__ == "__main__":
    unittest.main()
