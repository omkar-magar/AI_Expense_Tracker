"""
Budget service — daily limit logic.

Reads daily limit from settings, computes today's total, remaining amount,
and whether the limit has been exceeded.
"""

from database.queries import get_setting, set_setting, get_today_total


class BudgetService:

    def __init__(self, db):
        self.db = db

    def get_daily_limit(self) -> float:
        val = get_setting(self.db, "daily_limit")
        return float(val) if val else 500.0

    def set_daily_limit(self, amount: float):
        set_setting(self.db, "daily_limit", str(amount))

    def get_today_total(self) -> float:
        return get_today_total(self.db)

    def get_remaining(self) -> float:
        return max(0, self.get_daily_limit() - self.get_today_total())

    def is_limit_exceeded(self) -> bool:
        return self.get_today_total() >= self.get_daily_limit()

    def would_exceed(self, extra_amount: float) -> bool:
        """Whether adding `extra_amount` to today's confirmed spend crosses the
        limit — used to warn on a freshly captured (still pending) debit."""
        limit = self.get_daily_limit()
        if limit <= 0:
            return False
        return (self.get_today_total() + float(extra_amount)) >= limit

    def get_budget_summary(self) -> dict:
        limit = self.get_daily_limit()
        total = self.get_today_total()
        return {
            "daily_limit": limit,
            "today_total": total,
            "remaining": max(0, limit - total),
            "exceeded": total >= limit,
        }
