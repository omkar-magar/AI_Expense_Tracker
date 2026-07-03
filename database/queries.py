"""
Database query helpers.

Pure data-access functions — no business logic. Each function receives
a DatabaseManager instance and returns raw data (dicts/lists).
"""

from datetime import date


def get_setting(db, key):
    row = db.fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else None


def set_setting(db, key, value):
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def insert_transaction(db, txn: dict) -> int:
    cursor = db.execute(
        """INSERT INTO transactions
           (txn_date, txn_time, amount, merchant, source_app, txn_type, category, raw_notification)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            txn["txn_date"],
            txn["txn_time"],
            txn["amount"],
            txn.get("merchant"),
            txn.get("source_app", "PhonePe"),
            txn["txn_type"],
            txn.get("category", "Other"),
            txn.get("raw_notification"),
        ),
    )
    return cursor.lastrowid


def get_today_transactions(db):
    today = date.today().isoformat()
    rows = db.fetch_all(
        "SELECT * FROM transactions WHERE txn_date = ? AND txn_type = 'debit' ORDER BY txn_time DESC",
        (today,),
    )
    return [dict(row) for row in rows]


def delete_transaction(db, txn_id):
    # notification_logs.txn_id has a FK to transactions(id) and foreign_keys
    # is ON, so clear the reference before deleting or the DELETE fails with
    # "FOREIGN KEY constraint failed". Keep the log row (audit) but null the ref.
    db.execute("UPDATE notification_logs SET txn_id = NULL WHERE txn_id = ?", (txn_id,))
    db.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))


def get_today_total(db) -> float:
    today = date.today().isoformat()
    row = db.fetch_one(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE txn_date = ? AND txn_type = 'debit'",
        (today,),
    )
    return float(row["total"])


def find_duplicate(db, txn: dict, window_seconds=60) -> bool:
    """Check if a similar transaction exists within a time window."""
    row = db.fetch_one(
        """SELECT id FROM transactions
           WHERE txn_date = ?
             AND amount = ?
             AND COALESCE(merchant, '') = COALESCE(?, '')
             AND ABS(strftime('%s', txn_time) - strftime('%s', ?)) < ?
           LIMIT 1""",
        (
            txn["txn_date"],
            txn["amount"],
            txn.get("merchant"),
            txn["txn_time"],
            window_seconds,
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
