"""
Shared add / edit transaction editor (a popup) used by the dashboard (manual
add) and the transactions / review screens (edit & recategorize).

open_txn_editor(on_saved, txn=None):
  - txn is None  -> "Add Expense": inserts a confirmed manual transaction.
  - txn is a row -> "Edit": patches that transaction's amount/merchant/
    category/type in place.
on_saved() is called after a successful save so the caller can refresh.
"""

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup

from services.ai_service import CATEGORIES
from database.queries import add_manual_transaction, update_transaction

TXN_TYPES = ["debit", "credit"]


def _field_label(text):
    return Label(text=text, size_hint_y=None, height=dp(20), font_size=sp(12),
                 color=(0.62, 0.62, 0.72, 1), halign="left", valign="middle",
                 text_size=(dp(300), dp(20)))


def open_txn_editor(on_saved, txn=None):
    is_edit = txn is not None
    content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

    content.add_widget(_field_label("Amount (Rs.)"))
    amount_in = TextInput(
        text=("%g" % txn["amount"]) if is_edit else "",
        hint_text="e.g. 250", multiline=False, input_filter="float",
        size_hint_y=None, height=dp(44), font_size=sp(16),
    )
    content.add_widget(amount_in)

    content.add_widget(_field_label("Merchant / description"))
    merchant_in = TextInput(
        text=(txn.get("merchant") or "") if is_edit else "",
        hint_text="e.g. Swiggy", multiline=False,
        size_hint_y=None, height=dp(44), font_size=sp(16),
    )
    content.add_widget(merchant_in)

    row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    cat_spinner = Spinner(
        text=(txn.get("category") if is_edit and txn.get("category") in CATEGORIES else CATEGORIES[0]),
        values=CATEGORIES, font_size=sp(15),
    )
    type_spinner = Spinner(
        text=(txn.get("txn_type") if is_edit else "debit"),
        values=TXN_TYPES, font_size=sp(15),
    )
    row.add_widget(cat_spinner)
    row.add_widget(type_spinner)
    content.add_widget(row)

    error = Label(text="", size_hint_y=None, height=dp(20), font_size=sp(12),
                  color=(0.9, 0.35, 0.38, 1))
    content.add_widget(error)

    buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
    cancel_btn = Button(text="Cancel", background_normal="",
                        background_color=(0.30, 0.30, 0.40, 1), color=(1, 1, 1, 1))
    save_btn = Button(text=("Save" if is_edit else "Add"), background_normal="",
                      background_color=(0.22, 0.60, 0.45, 1), color=(1, 1, 1, 1))
    buttons.add_widget(cancel_btn)
    buttons.add_widget(save_btn)
    content.add_widget(buttons)

    popup = Popup(title=("Edit Transaction" if is_edit else "Add Expense"),
                  content=content, size_hint=(0.92, 0.72), auto_dismiss=False)

    def _save(*_):
        try:
            amount = float(amount_in.text)
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            error.text = "Enter a valid amount greater than 0"
            return
        app = App.get_running_app()
        merchant = merchant_in.text.strip() or None
        if is_edit:
            update_transaction(app.db, txn["id"], amount=amount, merchant=merchant,
                               category=cat_spinner.text, txn_type=type_spinner.text)
        else:
            add_manual_transaction(app.db, amount, merchant, cat_spinner.text,
                                   txn_type=type_spinner.text)
        popup.dismiss()
        if on_saved:
            on_saved()

    save_btn.bind(on_release=_save)
    cancel_btn.bind(on_release=lambda *_: popup.dismiss())
    popup.open()
