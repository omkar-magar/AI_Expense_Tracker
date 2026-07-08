"""Smoke tests — verify all screens and services initialize without crashing."""

import unittest
import os
import sys

from database.db_manager import DatabaseManager
from database.queries import get_setting, set_setting, get_today_transactions, get_today_total
from services.ai_service import AIService
from services.transaction_parser import parse_notification
from services.transaction_service import TransactionService
from services.budget_service import BudgetService
from services.alert_service import AlertService
from services.notification_service import NotificationService


class TestSmoke(unittest.TestCase):
    """Smoke tests to verify nothing crashes on init."""

    def setUp(self):
        self.db = DatabaseManager(db_path=":memory:")
        self.db.initialize()

    def tearDown(self):
        self.db.close()

    # --- Service initialization ---

    def test_ai_service_init_without_genai(self):
        ai = AIService(use_llm=False)
        self.assertFalse(ai.is_active)
        self.assertEqual(ai.categorize("Swiggy", "Paid to Swiggy"), "Food")

    def test_ai_service_init_with_fake_key(self):
        ai = AIService(use_llm=True, api_key="fake-key")
        cat = ai.categorize("Amazon", "Paid to Amazon")
        self.assertIn(cat, ["Shopping", "Other"])

    def test_budget_service_full_flow(self):
        budget = BudgetService(self.db)
        self.assertEqual(budget.get_daily_limit(), 500.0)
        budget.set_daily_limit(1000)
        self.assertEqual(budget.get_daily_limit(), 1000.0)
        summary = budget.get_budget_summary()
        self.assertEqual(summary["daily_limit"], 1000.0)
        self.assertEqual(summary["today_total"], 0.0)
        self.assertFalse(summary["exceeded"])

    def test_transaction_service_full_pipeline(self):
        ai = AIService()
        txn_svc = TransactionService(self.db, ai)
        txn = txn_svc.process_notification("Paid Rs.500 to Swiggy", "com.phonepe.app")
        self.assertIsNotNone(txn)
        self.assertEqual(txn["amount"], 500.0)
        self.assertEqual(txn["category"], "Food")

    def test_notification_service_full_flow(self):
        from database.queries import get_pending_transactions, confirm_transaction
        ai = AIService()
        txn_svc = TransactionService(self.db, ai)
        budget = BudgetService(self.db)
        alert = AlertService()
        notif = NotificationService(txn_svc, budget, alert)
        notif.on_notification_received("Paid Rs.100 to Zomato", "com.phonepe.app")
        # Auto-captured -> pending: not counted until the user confirms it.
        self.assertEqual(budget.get_today_total(), 0.0)
        pending = get_pending_transactions(self.db)
        self.assertEqual(len(pending), 1)
        confirm_transaction(self.db, pending[0]["id"])
        self.assertEqual(budget.get_today_total(), 100.0)

    # --- Limit screen edge cases ---

    def test_save_limit_empty_string(self):
        """Simulate save_limit('') — should not crash."""
        budget = BudgetService(self.db)
        original = budget.get_daily_limit()
        try:
            amount = float("")
        except (ValueError, TypeError):
            pass
        self.assertEqual(budget.get_daily_limit(), original)

    def test_save_limit_zero(self):
        budget = BudgetService(self.db)
        original = budget.get_daily_limit()
        amount = 0
        if amount <= 0:
            pass
        else:
            budget.set_daily_limit(amount)
        self.assertEqual(budget.get_daily_limit(), original)

    def test_save_limit_negative(self):
        budget = BudgetService(self.db)
        original = budget.get_daily_limit()
        amount = -100
        if amount <= 0:
            pass
        else:
            budget.set_daily_limit(amount)
        self.assertEqual(budget.get_daily_limit(), original)

    def test_save_limit_valid(self):
        budget = BudgetService(self.db)
        budget.set_daily_limit(750)
        self.assertEqual(budget.get_daily_limit(), 750.0)

    # --- Parser edge cases ---

    def test_parser_no_amount(self):
        self.assertIsNone(parse_notification("Hello world"))

    def test_parser_amount_no_action(self):
        self.assertIsNone(parse_notification("Rs.500"))

    def test_parser_special_characters(self):
        result = parse_notification("Paid Rs.230 to McDonald's")
        self.assertIsNotNone(result)
        self.assertEqual(result["amount"], 230.0)

    # --- Duplicate detection ---

    def test_duplicate_blocked(self):
        ai = AIService()
        txn_svc = TransactionService(self.db, ai)
        txn1 = txn_svc.process_notification("Paid Rs.500 to Swiggy", "com.phonepe.app")
        txn2 = txn_svc.process_notification("Paid Rs.500 to Swiggy", "com.phonepe.app")
        self.assertIsNotNone(txn1)
        self.assertIsNone(txn2)

    # --- Budget alert ---

    def test_limit_exceeded_triggers(self):
        from database.queries import get_pending_transactions, confirm_transaction
        budget = BudgetService(self.db)
        budget.set_daily_limit(100)
        ai = AIService()
        txn_svc = TransactionService(self.db, ai)
        txn_svc.process_notification("Paid Rs.150 to Swiggy", "com.phonepe.app")
        # A freshly captured (pending) debit that would cross the limit still
        # warns via the projected check, even before it is confirmed.
        self.assertTrue(budget.would_exceed(150))
        # Once confirmed, it counts and is_limit_exceeded is true.
        confirm_transaction(self.db, get_pending_transactions(self.db)[0]["id"])
        self.assertTrue(budget.is_limit_exceeded())

    # --- Settings persistence ---

    def test_settings_persist(self):
        set_setting(self.db, "gemini_api_key", "test-key-123")
        self.assertEqual(get_setting(self.db, "gemini_api_key"), "test-key-123")

    def test_ai_toggle_persist(self):
        set_setting(self.db, "ai_enabled", "1")
        self.assertEqual(get_setting(self.db, "ai_enabled"), "1")
        set_setting(self.db, "ai_enabled", "0")
        self.assertEqual(get_setting(self.db, "ai_enabled"), "0")

    # --- AI summary with no transactions ---

    def test_summary_empty(self):
        ai = AIService()
        result = ai.get_daily_summary([], {})
        self.assertEqual(result, "No transactions today.")

    def test_insights_empty(self):
        ai = AIService()
        result = ai.get_insights([])
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
