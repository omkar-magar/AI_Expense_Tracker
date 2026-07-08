"""
Database schema definitions.

Tables:
  - settings: stores app configuration (daily_limit, ai_enabled)
  - transactions: stores parsed transaction records
  - notification_logs: raw notification archive for debugging/reprocessing
  - daily_summary: cached daily aggregates (optional optimization)
"""

CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_TRANSACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_date          TEXT NOT NULL,       -- YYYY-MM-DD
    txn_time          TEXT NOT NULL,       -- HH:MM:SS
    amount            REAL NOT NULL,
    merchant          TEXT,
    source_app        TEXT DEFAULT 'PhonePe',
    txn_type          TEXT NOT NULL,       -- 'debit' or 'credit'
    category          TEXT DEFAULT 'Other',
    raw_notification  TEXT,
    status            TEXT DEFAULT 'confirmed',  -- 'pending' (awaiting review) or 'confirmed'
    created_at        TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

# Idempotent column migrations for databases created by an earlier schema.
# Each entry: (table, column, "ALTER TABLE ..." statement). Applied only when
# the column is missing, so re-running is safe.
COLUMN_MIGRATIONS = [
    ("transactions", "status",
     "ALTER TABLE transactions ADD COLUMN status TEXT DEFAULT 'confirmed'"),
]

CREATE_NOTIFICATION_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS notification_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    package_name    TEXT,
    title           TEXT,
    body            TEXT,
    received_at     TEXT DEFAULT (datetime('now', 'localtime')),
    processed       INTEGER DEFAULT 0,   -- 0=pending, 1=processed, -1=ignored
    txn_id          INTEGER,             -- FK to transactions.id if parsed
    FOREIGN KEY (txn_id) REFERENCES transactions(id)
);
"""

CREATE_DAILY_SUMMARY_TABLE = """
CREATE TABLE IF NOT EXISTS daily_summary (
    summary_date    TEXT PRIMARY KEY,     -- YYYY-MM-DD
    total_spent     REAL DEFAULT 0,
    txn_count       INTEGER DEFAULT 0,
    daily_limit     REAL,
    updated_at      TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

DEFAULT_SETTINGS = {
    "daily_limit": "500",
    "ai_enabled": "0",
}

ALL_TABLES = [
    CREATE_SETTINGS_TABLE,
    CREATE_TRANSACTIONS_TABLE,
    CREATE_NOTIFICATION_LOGS_TABLE,
    CREATE_DAILY_SUMMARY_TABLE,
]
