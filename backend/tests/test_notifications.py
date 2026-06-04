import unittest

from backend.app.core.config import settings
from backend.app.services.notifications import NotificationService


class NotificationServiceTest(unittest.TestCase):
    def test_run_issue_skips_when_webhook_is_not_configured(self):
        previous = settings.NOTIFICATION_WEBHOOK_URL
        settings.NOTIFICATION_WEBHOOK_URL = None
        try:
            result = NotificationService().notify_run_issue(
                "run_a",
                {
                    "ok": False,
                    "status": {"status": "error"},
                    "diagnosis": {
                        "analysis": {
                            "summary": {
                                "requires_operator": True,
                                "recommended_next_action": "notify_operator",
                                "risk_level": "critical",
                                "finding_count": 1,
                            }
                        }
                    },
                },
            )
        finally:
            settings.NOTIFICATION_WEBHOOK_URL = previous

        self.assertTrue(result["ok"])
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "webhook_not_configured")


if __name__ == "__main__":
    unittest.main()
