"""Transactions screen — shows full list of today's transactions."""

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty

from database.queries import get_today_transactions, delete_transaction
from screens.txn_editor import open_txn_editor


class TransactionsScreen(Screen):

    transactions = ListProperty([])

    def on_enter(self):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.transactions = get_today_transactions(app.db)

    def _find(self, txn_id):
        for t in self.transactions:
            if t.get("id") == txn_id:
                return t
        return None

    def edit_transaction(self, txn_id):
        txn = self._find(txn_id)
        if not txn:
            return
        open_txn_editor(self.refresh, txn=txn)

    def delete_transaction(self, txn_id):
        if not txn_id:
            return
        app = App.get_running_app()
        delete_transaction(app.db, txn_id)
        self.refresh()
