"""Tests for status/dedup/manual-entry backend (suggestions #1 dedup, #2, #3)."""

import unittest

from database.db_manager import DatabaseManager
from database.queries import (
    insert_transaction, add_manual_transaction, update_transaction,
    confirm_transaction, get_today_transactions, get_pending_transactions,
    get_today_total, pending_count, find_duplicate,
)
from services.transaction_service import TransactionService


def _txn(amount, merchant, source="PhonePe", ttype="debit", t="12:00:00"):
    from datetime import date
    return {
        "amount": amount, "merchant": merchant, "source_app": source,
        "txn_type": ttype, "category": "Other", "raw_notification": "x",
        "txn_date": date.today().isoformat(), "txn_time": t,
    }


class TestStatusAndTotals(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseManager(db_path=":memory:")
        self.db.initialize()

    def tearDown(self):
        self.db.close()

    def test_pending_excluded_from_total(self):
        insert_transaction(self.db, _txn(230, "Swiggy"), status="pending")
        self.assertEqual(get_today_total(self.db), 0.0)
        self.assertEqual(len(get_today_transactions(self.db)), 0)
        self.assertEqual(pending_count(self.db), 1)

    def test_confirm_moves_into_total(self):
        tid = insert_transaction(self.db, _txn(230, "Swiggy"), status="pending")
        confirm_transaction(self.db, tid)
        self.assertEqual(get_today_total(self.db), 230.0)
        self.assertEqual(pending_count(self.db), 0)
        self.assertEqual(len(get_today_transactions(self.db)), 1)

    def test_manual_is_confirmed_immediately(self):
        add_manual_transaction(self.db, 150, "Cash lunch", "Food")
        self.assertEqual(get_today_total(self.db), 150.0)
        self.assertEqual(pending_count(self.db), 0)

    def test_update_amount_and_category(self):
        tid = add_manual_transaction(self.db, 100, "X", "Other")
        update_transaction(self.db, tid, amount=250, category="Food")
        self.assertEqual(get_today_total(self.db), 250.0)
        row = get_today_transactions(self.db)[0]
        self.assertEqual(row["category"], "Food")

    def test_credit_not_in_spending_total(self):
        add_manual_transaction(self.db, 500, "Refund", "Other", txn_type="credit")
        self.assertEqual(get_today_total(self.db), 0.0)


class TestCrossSourceDedup(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseManager(db_path=":memory:")
        self.db.initialize()

    def tearDown(self):
        self.db.close()

    def test_sms_and_notification_same_payment_deduped(self):
        # PhonePe notification, then the bank SMS ~2 min later: different source
        # and different merchant text, same amount -> should be one transaction.
        insert_transaction(self.db, _txn(230, "Swiggy", source="PhonePe", t="12:00:00"),
                           status="pending")
        sms = _txn(230, "VPA swiggy@ybl", source="HDFCBK", t="12:02:00")
        self.assertTrue(find_duplicate(self.db, sms))

    def test_two_real_payments_same_source_not_deduped(self):
        # Two separate chai payments to different merchants from PhonePe.
        insert_transaction(self.db, _txn(50, "Chaiwala", source="PhonePe", t="12:00:00"),
                           status="pending")
        other = _txn(50, "Kirana", source="PhonePe", t="12:00:30")
        self.assertFalse(find_duplicate(self.db, other))

    def test_same_merchant_repeat_far_apart_not_deduped(self):
        insert_transaction(self.db, _txn(50, "Chaiwala", source="PhonePe", t="12:00:00"),
                           status="pending")
        later = _txn(50, "Chaiwala", source="PhonePe", t="12:05:00")  # 5 min later
        self.assertFalse(find_duplicate(self.db, later))


class TestServicePipelineStatus(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseManager(db_path=":memory:")
        self.db.initialize()
        self.svc = TransactionService(self.db, ai_service=None)

    def tearDown(self):
        self.db.close()

    def test_auto_capture_is_pending(self):
        txn = self.svc.process_notification("Paid ₹230 to Swiggy", "com.phonepe.app")
        self.assertIsNotNone(txn)
        self.assertEqual(txn["status"], "pending")
        self.assertEqual(get_today_total(self.db), 0.0)   # not counted yet
        self.assertEqual(pending_count(self.db), 1)

    def test_duplicate_second_capture_ignored(self):
        self.svc.process_notification("Paid ₹230 to Swiggy", "com.phonepe.app")
        dup = self.svc.process_notification("Debited ₹230 to swiggy@ybl", "HDFCBK")
        self.assertIsNone(dup)
        self.assertEqual(pending_count(self.db), 1)


if __name__ == "__main__":
    unittest.main()
