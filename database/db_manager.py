"""
Database connection manager.

Owns the SQLite connection lifecycle. All other modules access the DB
through this manager — no direct sqlite3 imports elsewhere.
"""

import os
import sqlite3

from database.schema import ALL_TABLES, DEFAULT_SETTINGS


DB_FILENAME = "expense_tracker.db"


class DatabaseManager:
    """Manages SQLite connection and initialization."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DB_FILENAME)
        self.db_path = db_path
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
        return self._conn

    def initialize(self):
        cursor = self.conn.cursor()
        for table_sql in ALL_TABLES:
            cursor.execute(table_sql)
        for key, value in DEFAULT_SETTINGS.items():
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        self.conn.commit()

    def execute(self, sql, params=None):
        cursor = self.conn.cursor()
        cursor.execute(sql, params or ())
        self.conn.commit()
        return cursor

    def fetch_one(self, sql, params=None):
        cursor = self.conn.cursor()
        cursor.execute(sql, params or ())
        return cursor.fetchone()

    def fetch_all(self, sql, params=None):
        cursor = self.conn.cursor()
        cursor.execute(sql, params or ())
        return cursor.fetchall()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
