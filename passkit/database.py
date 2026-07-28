"""SQLite access layer.

Deliberately dumb: this module never decrypts anything, it just moves
encrypted blobs and metadata in and out of the database. Decryption happens
one layer up in manager.py, only for the single entry that's actually
being looked at.
"""

import base64
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from . import config


@dataclass
class EntryMeta:
    """Everything about a saved entry except the password itself."""
    id: int
    website: str
    username: str
    created_at: str
    modified_at: str


@dataclass
class MasterRecord:
    salt: bytes
    password_hash: bytes


class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        self._create_tables()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _create_tables(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS master (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    website TEXT NOT NULL,
                    username TEXT NOT NULL,
                    encrypted_password TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    modified_at TEXT NOT NULL
                )
            """)

    # --- master password -------------------------------------------------

    def has_master_record(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM master WHERE id = 1").fetchone()
        return row is not None

    def save_master_record(self, salt: bytes, password_hash: bytes):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO master (id, salt, password_hash) VALUES (1, ?, ?)",
                (base64.b64encode(salt).decode(), base64.b64encode(password_hash).decode()),
            )

    def load_master_record(self) -> Optional[MasterRecord]:
        with self._connect() as conn:
            row = conn.execute("SELECT salt, password_hash FROM master WHERE id = 1").fetchone()
        if row is None:
            return None
        return MasterRecord(salt=base64.b64decode(row[0]), password_hash=base64.b64decode(row[1]))

    # --- entries -----------------------------------------------------------

    def insert_entry(self, website: str, username: str, encrypted_password: str) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO entries (website, username, encrypted_password, created_at, modified_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (website, username, encrypted_password, now, now),
            )
            return cursor.lastrowid

    def update_entry(self, entry_id: int, website: str, username: str, encrypted_password: str):
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE entries SET website = ?, username = ?, encrypted_password = ?, modified_at = ? "
                "WHERE id = ?",
                (website, username, encrypted_password, now, entry_id),
            )

    def delete_entry(self, entry_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))

    def list_entries(self, search: str = "") -> list[EntryMeta]:
        """Metadata only - no encrypted_password column, so a caller can't
        accidentally end up decrypting the whole vault just to render a list.
        """
        query = "SELECT id, website, username, created_at, modified_at FROM entries"
        params: tuple = ()
        if search:
            query += " WHERE website LIKE ? OR username LIKE ?"
            params = (f"%{search}%", f"%{search}%")
        query += " ORDER BY website COLLATE NOCASE"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [EntryMeta(*row) for row in rows]

    def get_encrypted_password(self, entry_id: int) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT encrypted_password FROM entries WHERE id = ?", (entry_id,)
            ).fetchone()
        return row[0] if row else None

    def replace_encrypted_password(self, entry_id: int, encrypted_password: str):
        """Used when re-encrypting under a new master password. Doesn't touch
        modified_at - swapping the encryption key isn't a content change.
        """
        with self._connect() as conn:
            conn.execute(
                "UPDATE entries SET encrypted_password = ? WHERE id = ?",
                (encrypted_password, entry_id),
            )
