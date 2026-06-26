"""Limit screen — allows user to set daily spending limit."""

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty


class LimitScreen(Screen):

    current_limit = StringProperty("")

    def on_enter(self):
        app = App.get_running_app()
        self.current_limit = str(int(app.budget_service.get_daily_limit()))

    def save_limit(self, value_text: str):
        try:
            amount = float(value_text)
            if amount <= 0:
                return
        except (ValueError, TypeError):
            return

        app = App.get_running_app()
        app.budget_service.set_daily_limit(amount)
        self.current_limit = str(int(amount))
        self.manager.current = "dashboard"
