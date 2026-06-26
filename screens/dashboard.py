"""
Dashboard screen — main app screen.

Shows today's date, daily limit, total spent, remaining budget,
AI-powered summary/insights, and a preview list of today's transactions.
Includes a simulate button for desktop testing.
"""

from datetime import date

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import StringProperty, NumericProperty, ListProperty


SAMPLE_NOTIFICATIONS = [
    "Paid Rs.230 to Swiggy",
    "Sent Rs.1000 to Rahul",
    "Paid Rs.350 to Amazon",
    "Paid Rs.150 to Uber",
    "Paid Rs.99 to Netflix",
    "Paid Rs.49 to Jio",
    "Paid Rs.500 to BigBasket",
    "Received Rs.2000 from Amit",
]


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

    def open_simulate_popup(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)

        text_input = TextInput(
            hint_text="e.g. Paid Rs.230 to Swiggy",
            multiline=False,
            size_hint_y=None,
            height=44,
            font_size=15,
        )
        content.add_widget(text_input)

        quick_label = Label(
            text="Or tap a sample:",
            size_hint_y=None,
            height=24,
            font_size=13,
            color=(0.6, 0.6, 0.7, 1),
        )
        content.add_widget(quick_label)

        popup = Popup(
            title="Simulate Notification",
            content=content,
            size_hint=(0.9, 0.75),
            auto_dismiss=True,
        )

        for sample in SAMPLE_NOTIFICATIONS:
            btn = Button(
                text=sample,
                size_hint_y=None,
                height=38,
                font_size=13,
                background_color=(0.25, 0.25, 0.35, 1),
            )
            btn.bind(on_release=lambda b, t=sample, p=popup: self._simulate_and_close(t, p))
            content.add_widget(btn)

        send_btn = Button(
            text="Send Custom",
            size_hint_y=None,
            height=44,
            font_size=15,
            background_color=(0.2, 0.6, 0.4, 1),
        )
        send_btn.bind(on_release=lambda b: self._simulate_and_close(text_input.text, popup))
        content.add_widget(send_btn)

        popup.open()

    def _simulate_and_close(self, text, popup):
        if not text.strip():
            return
        popup.dismiss()
        app = App.get_running_app()
        app.notification_service.on_notification_received(text.strip(), "com.phonepe.app")
        self.refresh()
