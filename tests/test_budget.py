"""Tests for the budget service."""

import os
import unittest
from database.db_manager import DatabaseManager
from services.budget_service import BudgetService


class TestBudgetService(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseManager(db_path=":memory:")
        self.db.initialize()
        self.budget = BudgetService(self.db)

    def test_default_limit(self):
        self.assertEqual(self.budget.get_daily_limit(), 500.0)

    def test_set_and_get_limit(self):
        self.budget.set_daily_limit(1000.0)
        self.assertEqual(self.budget.get_daily_limit(), 1000.0)

    def test_initial_total_is_zero(self):
        self.assertEqual(self.budget.get_today_total(), 0.0)

    def test_remaining_equals_limit_when_no_spending(self):
        self.assertEqual(self.budget.get_remaining(), 500.0)

    def test_not_exceeded_initially(self):
        self.assertFalse(self.budget.is_limit_exceeded())

    def test_budget_summary_structure(self):
        summary = self.budget.get_budget_summary()
        self.assertIn("daily_limit", summary)
        self.assertIn("today_total", summary)
        self.assertIn("remaining", summary)
        self.assertIn("exceeded", summary)

    def tearDown(self):
        self.db.close()


if __name__ == "__main__":
    unittest.main()
