"""
Database query helpers.

Pure data-access functions — no business logic. Each function receives
a DatabaseManager instance and returns raw data (dicts/lists).

Transactions have a `status`:
  - 'pending'   : auto-captured (SMS/notification), awaiting user review.
  - 'confirmed' : user-confirmed or manually added; counts toward spending.
Budget totals and the dashboard/all-transactions lists only ever consider
'confirmed' rows, so a mis-parsed auto-capture never silently inflates spend.
"""

from datetime import date, datetime


def get_setting(db, key):
    row = db.fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else None


def set_setting(db, key, value):
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def insert_transaction(db, txn: dict, status: str = "confirmed") -> int:
    cursor = db.execute(
        """INSERT INTO transactions
           (txn_date, txn_time, amount, merchant, source_app, txn_type, category, raw_notification, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            txn["txn_date"],
            txn["txn_time"],
            txn["amount"],
            txn.get("merchant"),
            txn.get("source_app", "PhonePe"),
            txn["txn_type"],
            txn.get("category", "Other"),
            txn.get("raw_notification"),
            status,
        ),
    )
    return cursor.lastrowid


def add_manual_transaction(db, amount, merchant, category, txn_type="debit") -> int:
    """Insert a user-entered transaction. Always 'confirmed' (the user typed it)."""
    now = datetime.now()
    txn = {
        "amount": float(amount),
        "merchant": merchant or "Manual entry",
        "source_app": "Manual",
        "txn_type": txn_type,
        "category": category or "Other",
        "raw_notification": None,
        "txn_date": now.strftime("%Y-%m-%d"),
        "txn_time": now.strftime("%H:%M:%S"),
    }
    return insert_transaction(db, txn, status="confirmed")


def update_transaction(db, txn_id, amount=None, merchant=None, category=None, txn_type=None):
    """Patch an existing transaction's editable fields (only non-None ones)."""
    fields, params = [], []
    if amount is not None:
        fields.append("amount = ?")
        params.append(float(amount))
    if merchant is not None:
        fields.append("merchant = ?")
        params.append(merchant)
    if category is not None:
        fields.append("category = ?")
        params.append(category)
    if txn_type is not None:
        fields.append("txn_type = ?")
        params.append(txn_type)
    if not fields:
        return
    params.append(txn_id)
    db.execute("UPDATE transactions SET %s WHERE id = ?" % ", ".join(fields), params)


def confirm_transaction(db, txn_id):
    """Move a pending auto-captured transaction into the confirmed set."""
    db.execute("UPDATE transactions SET status = 'confirmed' WHERE id = ?", (txn_id,))


def get_today_transactions(db):
    """Confirmed debits for today (dashboard + all-transactions views)."""
    today = date.today().isoformat()
    rows = db.fetch_all(
        "SELECT * FROM transactions "
        "WHERE txn_date = ? AND txn_type = 'debit' AND status = 'confirmed' "
        "ORDER BY txn_time DESC",
        (today,),
    )
    return [dict(row) for row in rows]


def get_pending_transactions(db):
    """Auto-captured transactions awaiting review (newest first, any type)."""
    rows = db.fetch_all(
        "SELECT * FROM transactions WHERE status = 'pending' "
        "ORDER BY txn_date DESC, txn_time DESC",
    )
    return [dict(row) for row in rows]


def pending_count(db) -> int:
    row = db.fetch_one("SELECT COUNT(*) AS c FROM transactions WHERE status = 'pending'")
    return int(row["c"]) if row else 0


def delete_transaction(db, txn_id):
    # notification_logs.txn_id has a FK to transactions(id) and foreign_keys
    # is ON, so clear the reference before deleting or the DELETE fails with
    # "FOREIGN KEY constraint failed". Keep the log row (audit) but null the ref.
    db.execute("UPDATE notification_logs SET txn_id = NULL WHERE txn_id = ?", (txn_id,))
    db.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))


def get_today_total(db) -> float:
    """Sum of today's confirmed debits."""
    today = date.today().isoformat()
    row = db.fetch_one(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
        "WHERE txn_date = ? AND txn_type = 'debit' AND status = 'confirmed'",
        (today,),
    )
    return float(row["total"])


def find_duplicate(db, txn: dict) -> bool:
    """Detect a repeat of the same payment.

    Two signals guard against the common double-count (the PhonePe notification
    AND the bank SMS for one payment):
      - same merchant, same amount/type, within 90s  -> duplicate; or
      - DIFFERENT source app (e.g. notification vs SMS), same amount/type,
        within 300s -> duplicate, even though the merchant text differs.
    A second genuine payment to a different merchant from the same source is
    NOT collapsed, because that requires either a merchant match or a source
    mismatch.
    """
    row = db.fetch_one(
        """SELECT id FROM transactions
           WHERE txn_date = ?
             AND amount = ?
             AND txn_type = ?
             AND (
                   (COALESCE(merchant, '') = COALESCE(?, '')
                        AND ABS(strftime('%s', txn_time) - strftime('%s', ?)) < 90)
                OR (COALESCE(source_app, '') <> COALESCE(?, '')
                        AND ABS(strftime('%s', txn_time) - strftime('%s', ?)) < 300)
             )
           LIMIT 1""",
        (
            txn["txn_date"],
            txn["amount"],
            txn["txn_type"],
            txn.get("merchant"),
            txn["txn_time"],
            txn.get("source_app", "PhonePe"),
            txn["txn_time"],
        ),
    )
    return row is not None


def log_notification(db, package_name, title, body, processed=0, txn_id=None):
    db.execute(
        """INSERT INTO notification_logs (package_name, title, body, processed, txn_id)
           VALUES (?, ?, ?, ?, ?)""",
        (package_name, title, body, processed, txn_id),
    )


def update_daily_summary(db, summary_date, total_spent, txn_count, daily_limit):
    db.execute(
        """INSERT INTO daily_summary (summary_date, total_spent, txn_count, daily_limit, updated_at)
           VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
           ON CONFLICT(summary_date) DO UPDATE SET
             total_spent = excluded.total_spent,
             txn_count = excluded.txn_count,
             daily_limit = excluded.daily_limit,
             updated_at = excluded.updated_at""",
        (summary_date, total_spent, txn_count, daily_limit),
    )
