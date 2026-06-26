"""End-to-end flow test — simulates notifications and checks the full pipeline."""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from database.db_manager import DatabaseManager
from database.queries import get_setting, get_today_transactions, set_setting
from services.ai_service import AIService
from services.transaction_service import TransactionService
from services.budget_service import BudgetService
from services.alert_service import AlertService
from services.notification_service import NotificationService

db = DatabaseManager()
db.initialize()

# Ensure AI is enabled for this test
api_key = get_setting(db, "gemini_api_key") or ""
if not api_key:
    print("WARNING: No Gemini API key found in database.")
    print("Run the Kivy app first and set it in Settings, or paste it below.")
    api_key = input("Gemini API Key (or press Enter to skip): ").strip()
    if api_key:
        set_setting(db, "gemini_api_key", api_key)
        set_setting(db, "ai_enabled", "1")

ai_enabled = get_setting(db, "ai_enabled") == "1"
ai = AIService(use_llm=ai_enabled, api_key=api_key)
txn_svc = TransactionService(db, ai)
budget = BudgetService(db)
alert = AlertService()
notif = NotificationService(txn_svc, budget, alert)

print(f"AI Active: {ai.is_active}")
print(f"Daily Limit: Rs.{budget.get_daily_limit():.0f}")
print("-" * 50)

notifications = [
    ("Paid Rs.230 to Swiggy", "com.phonepe.app"),
    ("Sent Rs.1000 to Rahul", "com.phonepe.app"),
    ("Paid Rs.350 to Amazon", "com.phonepe.app"),
    ("Received Rs.500 from Amit", "com.phonepe.app"),
    ("Paid Rs.150 to Uber", "com.phonepe.app"),
]

for text, pkg in notifications:
    print(f"\nProcessing: {text}")
    txn = txn_svc.process_notification(text, pkg)
    if txn:
        print(f"  -> Saved: Rs.{txn['amount']:.0f} | {txn['txn_type']} | {txn['merchant']} | Category: {txn['category']}")
    else:
        print(f"  -> Skipped (invalid or duplicate)")

print("\n" + "=" * 50)
print(f"Today Total:  Rs.{budget.get_today_total():.0f}")
print(f"Remaining:    Rs.{budget.get_remaining():.0f}")
print(f"Limit Exceeded: {budget.is_limit_exceeded()}")

txns = get_today_transactions(db)
print(f"Transactions saved: {len(txns)}")

print("\n" + "=" * 50)
summary = ai.get_daily_summary(txns, budget.get_budget_summary())
print(f"AI Summary:\n{summary}")

insights = ai.get_insights(txns)
if insights:
    print(f"\nAI Insights:\n{insights}")

db.close()
