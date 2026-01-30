"""
Event Store Migration Tests

PREDICTION: Initializing ProjectionStore against a legacy SQLite schema that lacks the
events.event_id column will succeed, backfill the missing column, and add the
event_id index without raising sqlite3 errors.

EXPERIMENT: Create a legacy events table without event_id, then initialize
ProjectionStore on the same database path.

OBSERVE: ProjectionStore initializes cleanly, events.event_id exists, and
idx_events_event_id is present in PRAGMA index_list.
"""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from supervisor.db import ProjectionStore


class TestProjectionStoreMigrations(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_migrate_", suffix=".sqlite")
        os.close(fd)

    def tearDown(self) -> None:
        Path(self.db_path).unlink(missing_ok=True)

    def test_events_event_id_migration_is_idempotent(self) -> None:
        """
        PREDICTION: ProjectionStore initialization upgrades a legacy events table that
        lacks event_id by adding the column and index without crashing.

        EXPERIMENT:
        1. Create a legacy events table without event_id.
        2. Initialize ProjectionStore with that database file.
        3. Query PRAGMA table_info and index_list for events.

        OBSERVE:
        - No sqlite3.OperationalError raised during initialization.
        - events table includes event_id column.
        - idx_events_event_id exists for events table.
        """
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                nats_seq INTEGER,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                type TEXT NOT NULL,
                payload JSON NOT NULL
            );
        """)
        conn.commit()
        conn.close()

        store = ProjectionStore(
            db_path=Path(self.db_path),
            user_id="local",
        )
        columns = {
            row["name"] for row in store.conn.execute("PRAGMA table_info(events)").fetchall()
        }
        indexes = {
            row["name"] for row in store.conn.execute("PRAGMA index_list(events)").fetchall()
        }
        store.close()

        self.assertIn("event_id", columns)
        self.assertIn("idx_events_event_id", indexes)
