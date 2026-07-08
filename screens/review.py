"""
Review inbox — auto-captured (SMS / notification) transactions land here as
'pending' and do NOT count toward spending until the user acts:

  - Confirm : mark 'confirmed' so it counts.
  - Edit    : fix amount/merchant/category, then confirm.
  - Dismiss : delete it (a mis-parse or a non-expense).

This makes fuzzy auto-capture trustworthy instead of silently wrong.
"""

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty

from database.queries import (
    get_pending_transactions, confirm_transaction, delete_transaction,
)
from screens.txn_editor import open_txn_editor


class ReviewScreen(Screen):

    transactions = ListProperty([])

    def on_enter(self):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.transactions = get_pending_transactions(app.db)

    def _find(self, txn_id):
        for t in self.transactions:
            if t.get("id") == txn_id:
                return t
        return None

    def confirm(self, txn_id):
        if not txn_id:
            return
        app = App.get_running_app()
        confirm_transaction(app.db, txn_id)
        self._after_change(app)

    def dismiss_txn(self, txn_id):
        if not txn_id:
            return
        app = App.get_running_app()
        delete_transaction(app.db, txn_id)
        self._after_change(app)

    def edit(self, txn_id):
        txn = self._find(txn_id)
        if not txn:
            return
        app = App.get_running_app()

        def _on_saved():
            # Editing a pending item implies the user accepts it -> confirm.
            confirm_transaction(app.db, txn_id)
            self._after_change(app)

        open_txn_editor(_on_saved, txn=txn)

    def _after_change(self, app):
        self.refresh()
        # Keep the dashboard total/badge in sync.
        try:
            app.root.get_screen("dashboard").refresh()
        except Exception:
            pass
