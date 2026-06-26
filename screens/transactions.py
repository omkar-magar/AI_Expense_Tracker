"""Transactions screen — shows full list of today's transactions."""

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty

from database.queries import get_today_transactions


class TransactionsScreen(Screen):

    transactions = ListProperty([])

    def on_enter(self):
        app = App.get_running_app()
        self.transactions = get_today_transactions(app.db)
