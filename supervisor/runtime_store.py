"""Runtime-local store for delivery dedupe and ephemeral state."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from shared.tenancy import get_default_user_id

DEFAULT_USER_ID = get_default_user_id()
DEFAULT_RUNTIME_PATH = Path(".context") / "runtime.sqlite"


class RuntimeStore:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        user_id: str = DEFAULT_USER_ID,
    ) -> None:
        self.user_id = user_id
        self.db_path = db_path or DEFAULT_RUNTIME_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS event_dedupe (
                consumer TEXT NOT NULL,
                event_id TEXT NOT NULL,
                status TEXT NOT NULL,
                nats_seq INTEGER,
                subject TEXT,
                delivery_count INTEGER NOT NULL DEFAULT 1,
                first_seen TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen TEXT NOT NULL DEFAULT (datetime('now')),
                last_error TEXT,
                PRIMARY KEY (consumer, event_id)
            );
            CREATE INDEX IF NOT EXISTS idx_event_dedupe_status ON event_dedupe(status);

            CREATE TABLE IF NOT EXISTS runtime_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def record_event_delivery(
        self,
        consumer: str,
        event_id: str,
        nats_seq: Optional[int],
        subject: str,
        delivery_count: int,
    ) -> tuple[bool, str]:
        now = datetime.now().isoformat()
        try:
            self.conn.execute(
                """
                INSERT INTO event_dedupe
                    (consumer, event_id, status, nats_seq, subject, delivery_count, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (consumer, event_id, "received", nats_seq, subject, delivery_count, now, now),
            )
            self.conn.commit()
            return True, "received"
        except sqlite3.IntegrityError:
            row = self.conn.execute(
                "SELECT status FROM event_dedupe WHERE consumer = ? AND event_id = ?",
                (consumer, event_id),
            ).fetchone()
            self.conn.execute(
                """
                UPDATE event_dedupe
                SET last_seen = ?, delivery_count = ?, nats_seq = COALESCE(?, nats_seq), subject = COALESCE(?, subject)
                WHERE consumer = ? AND event_id = ?
                """,
                (now, delivery_count, nats_seq, subject, consumer, event_id),
            )
            self.conn.commit()
            status = row["status"] if row else "unknown"
            return False, status

    def mark_event_processing(self, consumer: str, event_id: str) -> None:
        now = datetime.now().isoformat()
        self.conn.execute(
            "UPDATE event_dedupe SET status = ?, last_seen = ? WHERE consumer = ? AND event_id = ?",
            ("processing", now, consumer, event_id),
        )
        self.conn.commit()

    def mark_event_done(self, consumer: str, event_id: str) -> None:
        now = datetime.now().isoformat()
        self.conn.execute(
            "UPDATE event_dedupe SET status = ?, last_seen = ? WHERE consumer = ? AND event_id = ?",
            ("done", now, consumer, event_id),
        )
        self.conn.commit()

    def mark_event_failed(self, consumer: str, event_id: str, error: str) -> None:
        now = datetime.now().isoformat()
        self.conn.execute(
            "UPDATE event_dedupe SET status = ?, last_seen = ?, last_error = ? WHERE consumer = ? AND event_id = ?",
            ("failed", now, error, consumer, event_id),
        )
        self.conn.commit()

    def get_state(self, key: str) -> Optional[str]:
        cursor = self.conn.execute(
            "SELECT value FROM runtime_state WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        return row["value"] if row else None

    def set_state(self, key: str, value: str) -> None:
        self.conn.execute(
            """INSERT INTO runtime_state (key, value)
               VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
        self.conn.commit()

    def delete_state(self, key: str) -> None:
        self.conn.execute(
            "DELETE FROM runtime_state WHERE key = ?",
            (key,),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
