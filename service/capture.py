"""
Background capture service (Android, python-for-android).

Runs the SAME capture pipeline as the app, but in a separate long-lived
process so transactions are captured even when the UI is closed/backgrounded.
It reuses `SmsReader`/`NotificationBridge` via their headless `setup()` +
`poll_once()`/`drain_once()` methods, so there is no duplicated capture logic.

Safe to run alongside the in-app pollers:
  - SMS progress is a persisted id ('sms_last_id') in the shared DB, so whichever
    process polls first advances it and the other sees no duplicates.
  - The notification queue file is claimed atomically (rename), so only one
    drainer ever gets a given batch.

Wiring (buildozer.spec):
    services = capture:service/capture.py:foreground

NOTE: This is the one component that cannot be validated off-device. Verify on
a phone (see java/README_notifications.md → "Background service").
"""

import time

POLL_INTERVAL_SECONDS = 4


def _build_pipeline():
    from database.db_manager import DatabaseManager
    from database.queries import get_setting
    from services.ai_service import AIService
    from services.transaction_service import TransactionService
    from services.budget_service import BudgetService
    from services.alert_service import AlertService
    from services.notification_service import NotificationService

    db = DatabaseManager()
    db.initialize()

    ai_enabled = get_setting(db, "ai_enabled") == "1"
    api_key = get_setting(db, "gemini_api_key") or ""
    ai = AIService(use_llm=ai_enabled, api_key=api_key)

    txn = TransactionService(db, ai)
    budget = BudgetService(db)
    alert = AlertService()
    return db, NotificationService(txn, budget, alert)


def main():
    db, notification_service = _build_pipeline()

    from capture.sms_reader import SmsReader
    from capture.notification_bridge import NotificationBridge

    sms = SmsReader(notification_service, db)
    bridge = NotificationBridge(notification_service)
    sms_ready = sms.setup()
    bridge_ready = bridge.setup()
    print("[capture-service] started (sms=%s notif=%s)" % (sms_ready, bridge_ready))

    while True:
        try:
            if bridge_ready:
                bridge.drain_once()
            if sms_ready:
                sms.poll_once()
        except Exception as e:
            print("[capture-service] loop error: %s" % e)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
