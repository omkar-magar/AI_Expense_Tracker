"""
Dashboard screen — main app screen.

Shows today's date, daily limit, total spent, remaining budget,
AI-powered summary/insights, and a preview list of today's transactions.
"""

from datetime import date

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, NumericProperty, ListProperty


class DashboardScreen(Screen):

    today_date = StringProperty("")
    daily_limit = NumericProperty(0)
    today_total = NumericProperty(0)
    remaining = NumericProperty(0)
    transactions = ListProperty([])
    status_text = StringProperty("Within budget")
    status_color = ListProperty([0.2, 0.8, 0.2, 1])
    ai_summary = StringProperty("")
    ai_insights = StringProperty("")

    def on_enter(self):
        self.refresh()

    def refresh(self, *args):
        app = App.get_running_app()

        self.today_date = date.today().strftime("%A, %d %B %Y")

        summary = app.budget_service.get_budget_summary()
        self.daily_limit = summary["daily_limit"]
        self.today_total = summary["today_total"]
        self.remaining = summary["remaining"]

        if summary["exceeded"]:
            self.status_text = "LIMIT EXCEEDED!"
            self.status_color = [0.9, 0.2, 0.2, 1]
        else:
            self.status_text = "Within budget"
            self.status_color = [0.2, 0.8, 0.2, 1]

        from database.queries import get_today_transactions
        self.transactions = get_today_transactions(app.db)

        self.ai_summary = app.ai_service.get_daily_summary(self.transactions, summary)
        self.ai_insights = app.ai_service.get_insights(self.transactions)

        app.notification_service.set_dashboard_callback(self.refresh)
