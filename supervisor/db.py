"""
Projection store for ChoirOS events.

Event-sourced: NATS JetStream is the source of truth; libsql is a materialized projection.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import math

try:
    import libsql  # type: ignore
    LIBSQL_AVAILABLE = True
except Exception:
    libsql = None
    LIBSQL_AVAILABLE = False

from .event_contract import normalize_event_type
from shared.tenancy import get_default_user_id

DEFAULT_DB_DIR = Path(__file__).parent.parent / ".context" / "projections"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "projection-local.db"
DEFAULT_USER_ID = os.environ.get("CHOIROS_USER_ID", get_default_user_id())


def _resolve_db_url(user_id: str) -> str:
    raw = os.environ.get("CHOIROS_PROJECTION_DB_URL")
    if raw:
        return raw.format(user_id=user_id)
    DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
    return str(DEFAULT_DB_DIR / f"projection-{user_id}.db")


def _resolve_sync_url(user_id: str) -> Optional[str]:
    raw = os.environ.get("CHOIROS_PROJECTION_DB_SYNC_URL")
    if raw:
        return raw.format(user_id=user_id)
    return None


def _resolve_auth_token() -> Optional[str]:
    return os.environ.get("CHOIROS_PROJECTION_DB_AUTH_TOKEN")


class ProjectionStore:
    """Materialized projection store (libsql)."""

    def __init__(
        self,
        db_url: Optional[str] = None,
        db_path: Optional[Path] = None,
        user_id: str = DEFAULT_USER_ID,
    ):
        self.user_id = user_id
        resolved = db_url or (str(db_path) if db_path is not None else _resolve_db_url(user_id))
        self.db_url = resolved
        self.conn = self._connect(resolved)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _connect(self, db_url: str):
        if db_url.startswith("libsql://") or db_url.startswith("file:"):
            if not LIBSQL_AVAILABLE:
                raise RuntimeError("libsql is required for projection store")
            return libsql.connect(
                db_url,
                auth_token=_resolve_auth_token(),
                sync_url=_resolve_sync_url(self.user_id),
            )
        if LIBSQL_AVAILABLE:
            return libsql.connect(
                db_url,
                auth_token=_resolve_auth_token(),
                sync_url=_resolve_sync_url(self.user_id),
            )
        return sqlite3.connect(db_url, check_same_thread=False)

    def _init_schema(self):
        """Initialize database schema."""
        self.conn.executescript("""
            -- Core event log (append-only source of truth)
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                nats_seq INTEGER,  -- Sequence from NATS JetStream
                event_id TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                type TEXT NOT NULL,
                payload JSON NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_nats_seq ON events(nats_seq);

            -- Materialized: file state
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                content_hash TEXT,
                blob_url TEXT,
                updated_at TEXT NOT NULL
            );

            -- Materialized: conversations
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL DEFAULT (datetime('now')),
                title TEXT,
                last_seq INTEGER
            );

            -- Materialized: messages (denormalized for query convenience)
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER REFERENCES conversations(id),
                event_seq INTEGER REFERENCES events(seq),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id);

            -- Materialized: tool calls
            CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_seq INTEGER REFERENCES events(seq),
                tool_call_id TEXT,
                conversation_id INTEGER REFERENCES conversations(id),
                tool_name TEXT NOT NULL,
                tool_input JSON NOT NULL,
                tool_result JSON,
                timestamp TEXT NOT NULL
            );

            -- Materialized: AHDB state vector
            CREATE TABLE IF NOT EXISTS ahdb_state (
                key TEXT PRIMARY KEY,
                value JSON NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- Materialized: AHDB deltas
            CREATE TABLE IF NOT EXISTS ahdb_deltas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_seq INTEGER REFERENCES events(seq),
                delta JSON NOT NULL,
                timestamp TEXT NOT NULL
            );

            -- Proposed AHDB deltas (not asserted)
            CREATE TABLE IF NOT EXISTS ahdb_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_seq INTEGER REFERENCES events(seq),
                run_id TEXT,
                delta JSON NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            -- Work items (persisted work queue)
            CREATE TABLE IF NOT EXISTS work_items (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                acceptance_criteria TEXT,
                required_verifiers JSON,
                risk_tier TEXT,
                dependencies JSON,
                status TEXT NOT NULL,
                parent_id TEXT,
                runner_id TEXT,
                run_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- Runs (one work item per run)
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                work_item_id TEXT REFERENCES work_items(id),
                status TEXT NOT NULL,
                mode TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            );

            -- Run notes (typed)
            CREATE TABLE IF NOT EXISTS run_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT REFERENCES runs(id),
                note_type TEXT NOT NULL,
                body JSON NOT NULL,
                event_seq INTEGER REFERENCES events(seq),
                created_at TEXT NOT NULL
            );

            -- Verifier attestations (recorded per run)
            CREATE TABLE IF NOT EXISTS run_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT REFERENCES runs(id),
                attestation JSON NOT NULL,
                event_seq INTEGER REFERENCES events(seq),
                created_at TEXT NOT NULL
            );

            -- Commit requests (director approval gate)
            CREATE TABLE IF NOT EXISTS run_commit_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT REFERENCES runs(id),
                payload JSON NOT NULL,
                event_seq INTEGER REFERENCES events(seq),
                created_at TEXT NOT NULL
            );

            -- Git checkpoints
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commit_sha TEXT NOT NULL,
                last_event_seq INTEGER NOT NULL,
                last_nats_seq INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                message TEXT
            );

            CREATE TABLE IF NOT EXISTS projection_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            -- Sync state
            CREATE TABLE IF NOT EXISTS sync_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            -- Run inputs (initial prompts + follow-ups)
            CREATE TABLE IF NOT EXISTS run_inputs (
                id TEXT PRIMARY KEY,
                run_id TEXT REFERENCES runs(id),
                prompt TEXT NOT NULL,
                kind TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            -- User settings (provider config, etc)
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()
        # Idempotent, lightweight migrations for existing local databases.
        self._ensure_column("work_items", "runner_id", "TEXT")
        self._ensure_column("work_items", "run_id", "TEXT")
        self._ensure_column("events", "event_id", "TEXT")
        self._ensure_column("tool_calls", "tool_call_id", "TEXT")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_event_id ON events(event_id)")
        self.conn.commit()

    def _ensure_column(self, table: str, column: str, column_type: str) -> None:
        cursor = self.conn.execute(f"PRAGMA table_info({table})")
        columns = {row["name"] for row in cursor.fetchall()}
        if column in columns:
            return
        self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        self.conn.commit()


    def get_events(
        self,
        since_seq: int = 0,
        event_type: Optional[str] = None,
        limit: int = 1000
    ) -> list[dict]:
        """Get events from the log."""
        if event_type:
            cursor = self.conn.execute(
                "SELECT * FROM events WHERE seq > ? AND type = ? ORDER BY seq LIMIT ?",
                (since_seq, event_type, limit)
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM events WHERE seq > ? ORDER BY seq LIMIT ?",
                (since_seq, limit)
            )

        return [dict(row) for row in cursor.fetchall()]

    def get_events_between(
        self,
        since_seq: int = 0,
        until_seq: Optional[int] = None,
        limit: int = 500
    ) -> list[dict]:
        if until_seq is None:
            cursor = self.conn.execute(
                "SELECT * FROM events WHERE seq > ? ORDER BY seq LIMIT ?",
                (since_seq, limit)
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM events WHERE seq > ? AND seq <= ? ORDER BY seq LIMIT ?",
                (since_seq, until_seq, limit)
            )
        return [dict(row) for row in cursor.fetchall()]

    def build_context_heatmap(
        self,
        since_seq: int = 0,
        until_seq: Optional[int] = None,
        limit: int = 500
    ) -> dict:
        latest_seq = self.get_latest_seq() or 0
        if until_seq is None:
            until_seq = latest_seq
        events = self.get_events_between(since_seq, until_seq, limit)

        root_id = "context-root"
        nodes: dict[str, dict] = {
            root_id: {
                "id": root_id,
                "label": "Context",
                "type": "root",
                "event_count": 0,
                "last_seq": 0,
                "last_timestamp": None,
                "score": 0.0,
                "metadata": {},
            }
        }
        edges: dict[tuple[str, str, str], dict] = {}

        def bump_edge(source: str, target: str, edge_type: str, weight: float) -> None:
            key = (source, target, edge_type)
            if key not in edges:
                edges[key] = {
                    "source": source,
                    "target": target,
                    "type": edge_type,
                    "weight": 0.0,
                }
            edges[key]["weight"] += weight

        def update_node(
            node_id: str,
            label: str,
            node_type: str,
            event_seq: int,
            timestamp: Optional[str],
            metadata: Optional[dict] = None
        ) -> None:
            entry = nodes.get(node_id)
            if entry is None:
                entry = {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "event_count": 0,
                    "last_seq": 0,
                    "last_timestamp": None,
                    "score": 0.0,
                    "metadata": metadata or {},
                }
                nodes[node_id] = entry
            if metadata:
                entry["metadata"].update(metadata)
            entry["event_count"] += 1
            entry["last_seq"] = max(entry["last_seq"], event_seq)
            if timestamp:
                entry["last_timestamp"] = timestamp
            age = max(until_seq - event_seq, 0)
            entry["score"] += math.exp(-age / 40) if age else 1.0

        def add_root_edge(node_id: str, weight: float) -> None:
            if node_id != root_id:
                bump_edge(root_id, node_id, "context", weight)

        for event in events:
            event_type = event.get("type") or ""
            event_seq = int(event.get("seq") or 0)
            timestamp = event.get("timestamp")
            payload = event.get("payload")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {}
            payload = payload or {}

            if event_type.startswith("file."):
                path = payload.get("path") or payload.get("dest") or payload.get("destination") or "unknown"
                node_id = f"file:{path}"
                update_node(node_id, path, "file", event_seq, timestamp, {"path": path})
                add_root_edge(node_id, 1.0)
                continue

            if event_type == "tool.call":
                tool_name = payload.get("tool_name") or "tool"
                node_id = f"tool:{tool_name}"
                update_node(node_id, tool_name, "tool", event_seq, timestamp, {"tool_name": tool_name})
                add_root_edge(node_id, 0.8)
                conversation_id = payload.get("conversation_id")
                if conversation_id is not None:
                    convo_id = f"conversation:{conversation_id}"
                    update_node(convo_id, f"Conversation {conversation_id}", "conversation", event_seq, timestamp)
                    bump_edge(convo_id, node_id, "invokes", 0.6)
                continue

            if event_type == "message":
                role = payload.get("role") or "message"
                node_id = f"message:{role}"
                update_node(node_id, role.capitalize(), "message", event_seq, timestamp, {"role": role})
                conversation_id = payload.get("conversation_id")
                if conversation_id is not None:
                    convo_id = f"conversation:{conversation_id}"
                    update_node(convo_id, f"Conversation {conversation_id}", "conversation", event_seq, timestamp)
                    bump_edge(convo_id, node_id, "message", 0.7)
                else:
                    add_root_edge(node_id, 0.7)
                continue

            if event_type.startswith("note."):
                node_id = f"note:{event_type}"
                update_node(node_id, event_type, "note", event_seq, timestamp)
                add_root_edge(node_id, 0.5)
                continue

            if event_type.startswith("receipt."):
                node_id = f"receipt:{event_type}"
                update_node(node_id, event_type, "receipt", event_seq, timestamp)
                add_root_edge(node_id, 0.6)
                continue

            if event_type.startswith("artifact."):
                label = payload.get("name") or event_type
                node_id = f"artifact:{label}"
                update_node(node_id, label, "artifact", event_seq, timestamp)
                add_root_edge(node_id, 0.5)
                continue

            if event_type.startswith("mode.") or event_type.startswith("run."):
                label = payload.get("mode") or payload.get("run_id") or event_type
                node_id = f"run:{label}"
                update_node(node_id, str(label), "run", event_seq, timestamp)
                add_root_edge(node_id, 0.9)
                continue

            node_id = f"event:{event_type}"
            update_node(node_id, event_type or "event", "event", event_seq, timestamp)
            add_root_edge(node_id, 0.4)

        max_score = max((entry["score"] for entry in nodes.values()), default=1.0)
        response_nodes = []
        for entry in nodes.values():
            heat = entry["score"] / max_score if max_score else 0.0
            response_nodes.append({
                "id": entry["id"],
                "label": entry["label"],
                "type": entry["type"],
                "heat": round(heat, 3),
                "event_count": entry["event_count"],
                "last_seq": entry["last_seq"],
                "last_timestamp": entry["last_timestamp"],
                "metadata": entry["metadata"] or {},
            })

        response_edges = []
        for edge in edges.values():
            response_edges.append({
                "source": edge["source"],
                "target": edge["target"],
                "type": edge["type"],
                "weight": round(edge["weight"], 3),
            })

        return {
            "nodes": response_nodes,
            "edges": response_edges,
            "latest_seq": latest_seq,
            "since_seq": since_seq,
            "until_seq": until_seq,
            "event_count": len(events),
        }

    def get_event_paths_since(self, since_seq: int, event_types: Optional[list[str]] = None) -> list[str]:
        """Return unique file paths from events since a sequence number."""
        types = event_types or ["file.write", "file.delete", "file.move"]
        placeholders = ",".join("?" for _ in types)
        cursor = self.conn.execute(
            f"SELECT payload FROM events WHERE seq > ? AND type IN ({placeholders})",
            (since_seq, *types),
        )
        paths: set[str] = set()
        for row in cursor.fetchall():
            payload = json.loads(row["payload"])
            if not isinstance(payload, dict):
                continue
            if "path" in payload:
                paths.add(payload["path"])
            if "from" in payload:
                paths.add(payload["from"])
            if "to" in payload:
                paths.add(payload["to"])
        return sorted(paths)

    def get_latest_seq(self) -> int:
        """Get the latest event sequence number."""
        cursor = self.conn.execute("SELECT MAX(seq) FROM events")
        result = cursor.fetchone()[0]
        return result or 0

    def get_latest_nats_seq(self) -> Optional[int]:
        """Get the latest NATS sequence number we've processed."""
        cursor = self.conn.execute(
            "SELECT MAX(nats_seq) FROM events WHERE nats_seq IS NOT NULL"
        )
        result = cursor.fetchone()[0]
        return result

    def rebuild_projection_from_events(self) -> int:
        """
        Rebuild materialized projections from the existing SQLite event log.

        Returns the number of events replayed.
        """
        self.conn.executescript("""
            DELETE FROM files;
            DELETE FROM messages;
            DELETE FROM tool_calls;
            DELETE FROM conversations;
            DELETE FROM ahdb_state;
            DELETE FROM ahdb_deltas;
            DELETE FROM ahdb_proposals;
            DELETE FROM run_notes;
            DELETE FROM run_verifications;
            DELETE FROM run_commit_requests;
            DELETE FROM run_inputs;
        """)
        self.conn.commit()

        cursor = self.conn.execute(
            "SELECT seq, type, payload, timestamp FROM events ORDER BY seq"
        )
        count = 0
        for row in cursor.fetchall():
            payload = json.loads(row["payload"])
            self._materialize_projection(row["type"], payload, row["timestamp"], row["seq"])
            count += 1

        self.conn.commit()
        return count

    def apply_event(
        self,
        event_type: str,
        payload: dict,
        timestamp_ms: int,
        nats_seq: Optional[int] = None,
        event_id: Optional[str] = None,
    ) -> int:
        """Insert event into the log and materialize projections."""
        if nats_seq is not None:
            existing = self.conn.execute(
                "SELECT seq FROM events WHERE nats_seq = ?",
                (nats_seq,),
            ).fetchone()
            if existing:
                return existing["seq"]
        normalized_type = normalize_event_type(event_type)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000).isoformat()
        if event_id is None:
            event_id = str(uuid.uuid4())
        cursor = self.conn.execute(
            "INSERT INTO events (nats_seq, event_id, type, payload, timestamp) VALUES (?, ?, ?, ?, ?)",
            (nats_seq, event_id, normalized_type, json.dumps(payload), timestamp)
        )
        event_seq = cursor.lastrowid
        self._materialize_projection(normalized_type, payload, timestamp, event_seq)
        if nats_seq is not None:
            self.set_projection_state("last_nats_seq", str(nats_seq), commit=False)
        return event_seq

    def _materialize_projection(
        self,
        event_type: str,
        payload: dict,
        timestamp: str,
        event_seq: int,
    ) -> None:
        """Materialize a single event into SQLite projection tables."""
        # Update materialized tables based on type
        if event_type == "file.write":
            self.conn.execute(
                """INSERT OR REPLACE INTO files (path, content_hash, updated_at)
                   VALUES (?, ?, ?)""",
                (payload.get("path"), payload.get("content_hash"), timestamp)
            )
        elif event_type == "file.delete":
            self.conn.execute("DELETE FROM files WHERE path = ?", (payload.get("path"),))
        elif event_type == "message":
            conversation_id = payload.get("conversation_id")
            if conversation_id is not None:
                self._ensure_conversation(conversation_id, timestamp)
            self.conn.execute(
                """INSERT INTO messages
                   (conversation_id, event_seq, role, content, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    conversation_id,
                    event_seq,
                    payload.get("role"),
                    payload.get("content"),
                    timestamp,
                )
            )
            if conversation_id is not None:
                self.conn.execute(
                    "UPDATE conversations SET last_seq = ? WHERE id = ?",
                    (event_seq, conversation_id)
                )
        elif event_type == "tool.call":
            conversation_id = payload.get("conversation_id")
            if conversation_id is not None:
                self._ensure_conversation(conversation_id, timestamp)
            self.conn.execute(
                """INSERT INTO tool_calls
                   (event_seq, tool_call_id, conversation_id, tool_name, tool_input, tool_result, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_seq,
                    payload.get("tool_call_id"),
                    conversation_id,
                    payload.get("tool_name"),
                    json.dumps(payload.get("tool_input")),
                    json.dumps(payload.get("tool_result")),
                    timestamp,
                )
            )
        elif event_type == "tool.result":
            tool_call_id = payload.get("tool_call_id")
            conversation_id = payload.get("conversation_id")
            if conversation_id is not None:
                self._ensure_conversation(conversation_id, timestamp)
            tool_result = json.dumps(payload.get("tool_result"))
            if tool_call_id:
                cursor = self.conn.execute(
                    "UPDATE tool_calls SET tool_result = ?, timestamp = ? WHERE tool_call_id = ?",
                    (tool_result, timestamp, tool_call_id),
                )
                if cursor.rowcount == 0:
                    self.conn.execute(
                        """INSERT INTO tool_calls
                           (event_seq, tool_call_id, conversation_id, tool_name, tool_input, tool_result, timestamp)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            event_seq,
                            tool_call_id,
                            conversation_id,
                            payload.get("tool_name"),
                            json.dumps(payload.get("tool_input") or {}),
                            tool_result,
                            timestamp,
                        ),
                    )
            else:
                self.conn.execute(
                    """INSERT INTO tool_calls
                       (event_seq, tool_call_id, conversation_id, tool_name, tool_input, tool_result, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event_seq,
                        None,
                        conversation_id,
                        payload.get("tool_name"),
                        json.dumps(payload.get("tool_input") or {}),
                        tool_result,
                        timestamp,
                    ),
                )
        elif event_type == "run.input":
            run_id = payload.get("run_id")
            prompt = payload.get("prompt")
            kind = payload.get("input_kind") or "initial"
            work_item_id = payload.get("work_item_id")
            runner_id = payload.get("session_id")
            description = prompt or payload.get("description")
            if work_item_id:
                self._ensure_work_item(
                    work_item_id,
                    description,
                    payload.get("status") or "queued",
                    runner_id,
                    run_id,
                    timestamp,
                    acceptance_criteria=payload.get("acceptance_criteria"),
                    required_verifiers=payload.get("required_verifiers"),
                    risk_tier=payload.get("risk_tier"),
                    dependencies=payload.get("dependencies"),
                    parent_id=payload.get("parent_id"),
                )
            if run_id:
                self._ensure_run(run_id, work_item_id, "queued", None, timestamp)
            if run_id and prompt:
                self.conn.execute(
                    """INSERT INTO run_inputs (id, run_id, prompt, kind, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), run_id, prompt, kind, timestamp),
                )
        elif event_type == "run.started":
            run_id = payload.get("run_id")
            work_item_id = payload.get("work_item_id")
            mode = payload.get("mode")
            if run_id:
                self._ensure_run(run_id, work_item_id, "running", mode, timestamp)
                self.conn.execute(
                    "UPDATE runs SET started_at = COALESCE(started_at, ?), updated_at = ? WHERE id = ?",
                    (timestamp, timestamp, run_id),
                )
            if work_item_id:
                self._ensure_work_item(work_item_id, None, "running", payload.get("session_id"), run_id, timestamp)
        elif event_type == "run.finished":
            run_id = payload.get("run_id")
            work_item_id = payload.get("work_item_id")
            status = payload.get("status") or "finished"
            mode = payload.get("mode")
            if run_id:
                self._ensure_run(run_id, work_item_id, status, mode, timestamp)
                self.conn.execute(
                    "UPDATE runs SET finished_at = ?, updated_at = ? WHERE id = ?",
                    (timestamp, timestamp, run_id),
                )
            if work_item_id:
                terminal_status = "completed"
                if str(status).lower() in {"failed", "error"}:
                    terminal_status = "failed"
                self._ensure_work_item(work_item_id, None, terminal_status, payload.get("session_id"), run_id, timestamp)
        elif event_type == "mode.start":
            run_id = payload.get("run_id")
            work_item_id = payload.get("work_item_id")
            mode = payload.get("mode")
            if run_id:
                self._ensure_run(run_id, work_item_id, "running", mode, timestamp)
            if work_item_id:
                self._ensure_work_item(work_item_id, payload.get("prompt"), "running", payload.get("session_id"), run_id, timestamp)
        elif event_type == "mode.update":
            run_id = payload.get("run_id")
            status = payload.get("status")
            mode = payload.get("mode")
            if run_id:
                self._ensure_run(run_id, payload.get("work_item_id"), status or "running", mode, timestamp)
        elif event_type == "receipt.ahdb.delta":
            delta = self._extract_ahdb_delta(payload)
            if delta is not None:
                authority = None
                if isinstance(payload, dict):
                    authority = payload.get("authority")
                if authority == "proposed":
                    run_id = payload.get("run_id") if isinstance(payload, dict) else None
                    self._apply_ahdb_proposal(delta, run_id, timestamp, event_seq)
                else:
                    self._apply_ahdb_delta(delta, timestamp, event_seq)
                    if authority == "asserted" and isinstance(payload, dict):
                        run_id = payload.get("run_id")
                        if run_id:
                            self.conn.execute(
                                "UPDATE ahdb_proposals SET status = ? WHERE run_id = ? AND status = ?",
                                ("promoted", run_id, "proposed"),
                            )
        elif event_type.startswith("note."):
            run_id = payload.get("run_id")
            body = payload.get("body", payload)
            if run_id:
                self.conn.execute(
                    """INSERT INTO run_notes (run_id, note_type, body, event_seq, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (run_id, event_type, json.dumps(body), event_seq, timestamp),
                )
            if event_type == "note.request.verify" and run_id:
                self.conn.execute(
                    """INSERT INTO run_commit_requests (run_id, payload, event_seq, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (run_id, json.dumps(body), event_seq, timestamp),
                )
            if event_type == "note.status" and run_id and isinstance(body, dict):
                status = body.get("status")
                mode = body.get("mode")
                if status:
                    self._ensure_run(run_id, None, status, mode, timestamp)
        elif event_type == "receipt.verifier.attestations":
            run_id = payload.get("run_id")
            attestation = payload.get("attestation")
            if run_id and attestation is not None:
                self.conn.execute(
                    """INSERT INTO run_verifications (run_id, attestation, event_seq, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (run_id, json.dumps(attestation), event_seq, timestamp),
                )
        elif event_type == "provider.changed":
            provider = payload.get("provider")
            if provider:
                self.conn.execute(
                    """INSERT INTO user_settings (key, value, updated_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
                    ("llm_provider", provider, timestamp),
                )
        elif event_type == "checkpoint":
            commit_sha = payload.get("commit_sha")
            message = payload.get("message")
            if commit_sha:
                self.conn.execute(
                    """INSERT INTO checkpoints (commit_sha, last_event_seq, last_nats_seq, message)
                       VALUES (?, ?, ?, ?)""",
                    (commit_sha, event_seq, payload.get("nats_seq"), message),
                )
                if payload.get("mark_good"):
                    self.conn.execute(
                        """INSERT INTO sync_state (key, value)
                           VALUES (?, ?)
                           ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                        ("last_good_checkpoint", commit_sha),
                    )

    def _extract_ahdb_delta(self, payload: dict) -> Optional[dict]:
        if not isinstance(payload, dict):
            return None
        for key in ("delta", "ahdb_delta", "ahdb"):
            if key in payload and isinstance(payload[key], dict):
                return payload[key]
        if any(k in payload for k in ("assert", "hypothesize", "drive", "believe")):
            return {k: payload.get(k) for k in ("assert", "hypothesize", "drive", "believe") if k in payload}
        return None

    def _apply_ahdb_delta(self, delta: dict, timestamp: str, event_seq: int) -> None:
        self.conn.execute(
            "INSERT INTO ahdb_deltas (event_seq, delta, timestamp) VALUES (?, ?, ?)",
            (event_seq, json.dumps(delta), timestamp)
        )
        for key, value in delta.items():
            if key is None:
                continue
            self.conn.execute(
                """INSERT OR REPLACE INTO ahdb_state (key, value, updated_at)
                   VALUES (?, ?, ?)""",
                (key, json.dumps(value), timestamp)
            )

    def _apply_ahdb_proposal(
        self,
        delta: dict,
        run_id: Optional[str],
        timestamp: str,
        event_seq: int,
    ) -> None:
        self.conn.execute(
            """INSERT INTO ahdb_proposals (event_seq, run_id, delta, status, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (event_seq, run_id, json.dumps(delta), "proposed", timestamp),
        )

    def _ensure_conversation(self, conversation_id: int, started_at: str) -> None:
        """Ensure a conversation row exists for materialization."""
        cursor = self.conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        if cursor.fetchone():
            return
        self.conn.execute(
            "INSERT INTO conversations (id, started_at, last_seq) VALUES (?, ?, ?)",
            (conversation_id, started_at, None)
        )

    def _ensure_work_item(
        self,
        work_item_id: str,
        description: Optional[str],
        status: str,
        runner_id: Optional[str],
        run_id: Optional[str],
        timestamp: str,
        acceptance_criteria: Optional[str] = None,
        required_verifiers: Optional[list[str]] = None,
        risk_tier: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
        parent_id: Optional[str] = None,
    ) -> None:
        required_json = json.dumps(required_verifiers) if required_verifiers is not None else None
        deps_json = json.dumps(dependencies) if dependencies is not None else None
        self.conn.execute(
            """INSERT OR IGNORE INTO work_items
               (id, description, acceptance_criteria, required_verifiers, risk_tier,
                dependencies, status, parent_id, runner_id, run_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                work_item_id,
                description,
                acceptance_criteria,
                required_json or json.dumps([]),
                risk_tier,
                deps_json or json.dumps([]),
                status,
                parent_id,
                runner_id,
                run_id,
                timestamp,
                timestamp,
            ),
        )
        self.conn.execute(
            """UPDATE work_items
               SET description = COALESCE(?, description),
                   acceptance_criteria = COALESCE(?, acceptance_criteria),
                   required_verifiers = COALESCE(?, required_verifiers),
                   risk_tier = COALESCE(?, risk_tier),
                   dependencies = COALESCE(?, dependencies),
                   parent_id = COALESCE(?, parent_id),
                   status = ?,
                   runner_id = COALESCE(?, runner_id),
                   run_id = COALESCE(?, run_id),
                   updated_at = ?
               WHERE id = ?""",
            (
                description,
                acceptance_criteria,
                required_json,
                risk_tier,
                deps_json,
                parent_id,
                status,
                runner_id,
                run_id,
                timestamp,
                work_item_id,
            ),
        )

    def _ensure_run(
        self,
        run_id: str,
        work_item_id: Optional[str],
        status: str,
        mode: Optional[str],
        timestamp: str,
    ) -> None:
        self.conn.execute(
            """INSERT OR IGNORE INTO runs
               (id, work_item_id, status, mode, created_at, updated_at, started_at, finished_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, work_item_id, status, mode, timestamp, timestamp, None, None),
        )
        self.conn.execute(
            """UPDATE runs
               SET work_item_id = COALESCE(?, work_item_id),
                   status = ?,
                   mode = COALESCE(?, mode),
                   updated_at = ?
               WHERE id = ?""",
            (work_item_id, status, mode, timestamp, run_id),
        )

    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: int = 100
    ) -> list[dict]:
        """Get messages for a conversation."""
        cursor = self.conn.execute(
            """SELECT role, content, timestamp
               FROM messages
               WHERE conversation_id = ?
               ORDER BY id DESC LIMIT ?""",
            (conversation_id, limit)
        )
        # Reverse to get chronological order
        return list(reversed([dict(row) for row in cursor.fetchall()]))

    def list_tool_calls(self, conversation_id: int) -> list[dict]:
        cursor = self.conn.execute(
            """SELECT event_seq, tool_call_id, tool_name, tool_input, tool_result, timestamp
               FROM tool_calls
               WHERE conversation_id = ?
               ORDER BY event_seq ASC""",
            (conversation_id,),
        )
        results: list[dict] = []
        for row in cursor.fetchall():
            tool_input = json.loads(row["tool_input"]) if row["tool_input"] else {}
            tool_result = json.loads(row["tool_result"]) if row["tool_result"] else None
            results.append(
                {
                    "event_seq": row["event_seq"],
                    "tool_call_id": row["tool_call_id"],
                    "tool_name": row["tool_name"],
                    "tool_input": tool_input,
                    "tool_result": tool_result,
                    "timestamp": row["timestamp"],
                }
            )
        return results

    def get_ahdb_state(self) -> dict:
        """Return the latest AHDB state vector."""
        cursor = self.conn.execute("SELECT key, value FROM ahdb_state")
        state: dict = {}
        for row in cursor.fetchall():
            state[row["key"]] = json.loads(row["value"])
        return state

    def list_ahdb_proposals(self, run_id: Optional[str] = None) -> list[dict]:
        if run_id:
            cursor = self.conn.execute(
                "SELECT * FROM ahdb_proposals WHERE run_id = ? ORDER BY id DESC",
                (run_id,),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM ahdb_proposals ORDER BY id DESC"
            )
        proposals: list[dict] = []
        for row in cursor.fetchall():
            entry = dict(row)
            delta = entry.get("delta")
            if delta:
                try:
                    entry["delta"] = json.loads(delta)
                except json.JSONDecodeError:
                    pass
            proposals.append(entry)
        return proposals

    def mark_ahdb_proposals_promoted(self, run_id: str) -> None:
        self.conn.execute(
            "UPDATE ahdb_proposals SET status = ? WHERE run_id = ? AND status = ?",
            ("promoted", run_id, "proposed"),
        )
        self.conn.commit()

    # =========== Work Items ===========

    def create_work_item(
        self,
        description: str,
        acceptance_criteria: Optional[str] = None,
        required_verifiers: Optional[list[str]] = None,
        risk_tier: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
        status: str = "pending",
        parent_id: Optional[str] = None,
        runner_id: Optional[str] = None,
    ) -> dict:
        """Create a work item."""
        now = datetime.now().isoformat()
        work_item_id = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO work_items
               (id, description, acceptance_criteria, required_verifiers, risk_tier,
                dependencies, status, parent_id, runner_id, run_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                work_item_id,
                description,
                acceptance_criteria,
                json.dumps(required_verifiers or []),
                risk_tier,
                json.dumps(dependencies or []),
                status,
                parent_id,
                runner_id,
                None,
                now,
                now,
            ),
        )
        self.conn.commit()
        run = self.create_run(work_item_id=work_item_id, status="created")
        if status == "queued":
            self.update_run(run["id"], {"status": "queued"})
        return self.update_work_item(work_item_id, {"run_id": run["id"]})

    def update_work_item(self, work_item_id: str, updates: dict) -> Optional[dict]:
        """Update fields on a work item."""
        allowed = {
            "description",
            "acceptance_criteria",
            "required_verifiers",
            "risk_tier",
            "dependencies",
            "status",
            "parent_id",
            "runner_id",
            "run_id",
        }
        fields = {k: updates[k] for k in updates if k in allowed}
        if not fields:
            return self.get_work_item(work_item_id)

        if "required_verifiers" in fields:
            fields["required_verifiers"] = json.dumps(fields["required_verifiers"] or [])
        if "dependencies" in fields:
            fields["dependencies"] = json.dumps(fields["dependencies"] or [])

        fields["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{key} = ?" for key in fields.keys())
        values = list(fields.values()) + [work_item_id]
        self.conn.execute(f"UPDATE work_items SET {set_clause} WHERE id = ?", values)
        self.conn.commit()
        return self.get_work_item(work_item_id)

    def claim_next_work_item(self, runner_id: str) -> Optional[dict]:
        """
        Atomically claim the next queued work item.

        This prevents multiple websocket sessions from executing the same prompt.
        """
        now = datetime.now().isoformat()
        with self.conn:
            row = self.conn.execute(
                """
                SELECT id FROM work_items
                WHERE status = 'queued' AND (runner_id IS NULL OR runner_id = ?)
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (runner_id,),
            ).fetchone()
            if not row:
                return None
            work_item_id = row["id"]
            cursor = self.conn.execute(
                """
                UPDATE work_items
                SET status = 'running', runner_id = ?, updated_at = ?
                WHERE id = ? AND status = 'queued' AND (runner_id IS NULL OR runner_id = ?)
                """,
                (runner_id, now, work_item_id, runner_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_work_item(work_item_id)

    def get_or_create_run_for_work_item(self, work_item_id: str) -> Optional[dict]:
        work_item = self.get_work_item(work_item_id)
        if not work_item:
            return None
        run_id = work_item.get("run_id")
        if run_id:
            run = self.get_run(run_id)
            if run:
                return run
        run = self.create_run(work_item_id=work_item_id, status="created")
        self.update_work_item(work_item_id, {"run_id": run["id"]})
        return run

    def get_work_item(self, work_item_id: str) -> Optional[dict]:
        cursor = self.conn.execute("SELECT * FROM work_items WHERE id = ?", (work_item_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._deserialize_work_item(dict(row))

    def list_work_items(self, status: Optional[str] = None, limit: int = 50) -> list[dict]:
        if status:
            cursor = self.conn.execute(
                "SELECT * FROM work_items WHERE status = ? ORDER BY created_at ASC LIMIT ?",
                (status, limit),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM work_items ORDER BY created_at ASC LIMIT ?",
                (limit,),
            )
        return [self._deserialize_work_item(dict(row)) for row in cursor.fetchall()]

    def _deserialize_work_item(self, row: dict) -> dict:
        row["required_verifiers"] = json.loads(row.get("required_verifiers") or "[]")
        row["dependencies"] = json.loads(row.get("dependencies") or "[]")
        return row

    # =========== Runs ===========

    def create_run(
        self,
        work_item_id: str,
        mode: Optional[str] = None,
        status: str = "created",
    ) -> dict:
        now = datetime.now().isoformat()
        run_id = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO runs
               (id, work_item_id, status, mode, created_at, updated_at, started_at, finished_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, work_item_id, status, mode, now, now, None, None),
        )
        self.conn.commit()
        return self.get_run(run_id)

    def update_run(self, run_id: str, updates: dict) -> Optional[dict]:
        allowed = {"status", "mode", "started_at", "finished_at"}
        fields = {k: updates[k] for k in updates if k in allowed}
        if not fields:
            return self.get_run(run_id)
        fields["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{key} = ?" for key in fields.keys())
        values = list(fields.values()) + [run_id]
        self.conn.execute(f"UPDATE runs SET {set_clause} WHERE id = ?", values)
        self.conn.commit()
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> Optional[dict]:
        cursor = self.conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_latest_run_for_work_item(self, work_item_id: str) -> Optional[dict]:
        cursor = self.conn.execute(
            "SELECT * FROM runs WHERE work_item_id = ? ORDER BY created_at DESC LIMIT 1",
            (work_item_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_runs(self, status: Optional[str] = None, limit: int = 50) -> list[dict]:
        if status:
            cursor = self.conn.execute(
                "SELECT * FROM runs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]

    def list_runs_with_work_items(self, status: Optional[str] = None, limit: int = 50) -> list[dict]:
        if status:
            cursor = self.conn.execute(
                """
                SELECT runs.*, work_items.description AS prompt, work_items.status AS work_item_status
                FROM runs
                JOIN work_items ON work_items.id = runs.work_item_id
                WHERE runs.status = ?
                ORDER BY runs.created_at DESC
                LIMIT ?
                """,
                (status, limit),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT runs.*, work_items.description AS prompt, work_items.status AS work_item_status
                FROM runs
                JOIN work_items ON work_items.id = runs.work_item_id
                ORDER BY runs.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]

    def get_run_with_work_item(self, run_id: str) -> Optional[dict]:
        cursor = self.conn.execute(
            """
            SELECT runs.*, work_items.description AS prompt, work_items.status AS work_item_status
            FROM runs
            JOIN work_items ON work_items.id = runs.work_item_id
            WHERE runs.id = ?
            LIMIT 1
            """,
            (run_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def add_run_input(self, run_id: str, prompt: str, kind: str = "initial") -> dict:
        now = datetime.now().isoformat()
        run_input_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO run_inputs (id, run_id, prompt, kind, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_input_id, run_id, prompt, kind, now),
        )
        self.conn.commit()
        return {
            "id": run_input_id,
            "run_id": run_id,
            "prompt": prompt,
            "kind": kind,
            "created_at": now,
        }

    def list_run_inputs(self, run_id: str, limit: int = 200) -> list[dict]:
        cursor = self.conn.execute(
            """
            SELECT * FROM run_inputs
            WHERE run_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (run_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    # =========== Checkpoints ===========

    def record_checkpoint(self, commit_sha: str, message: str = None, commit: bool = True) -> int:
        """Record a git checkpoint."""
        last_seq = self.get_latest_seq()
        last_nats_seq = self.get_latest_nats_seq()

        cursor = self.conn.execute(
            """INSERT INTO checkpoints (commit_sha, last_event_seq, last_nats_seq, message)
               VALUES (?, ?, ?, ?)""",
            (commit_sha, last_seq, last_nats_seq, message)
        )
        if commit:
            self.conn.commit()
        return cursor.lastrowid

    def get_last_checkpoint(self) -> Optional[dict]:
        """Get the most recent checkpoint."""
        cursor = self.conn.execute(
            "SELECT * FROM checkpoints ORDER BY created_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    # =========== Projection State ===========

    def get_projection_state(self, key: str) -> Optional[str]:
        cursor = self.conn.execute(
            "SELECT value FROM projection_state WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        return row["value"] if row else None

    def set_projection_state(self, key: str, value: str, commit: bool = True) -> None:
        self.conn.execute(
            """INSERT INTO projection_state (key, value)
               VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
        if commit:
            self.conn.commit()

    def delete_projection_state(self, key: str, commit: bool = True) -> None:
        self.conn.execute(
            "DELETE FROM projection_state WHERE key = ?",
            (key,),
        )
        if commit:
            self.conn.commit()

    # =========== Sync State ===========

    def get_sync_state(self, key: str) -> Optional[str]:
        """Get a sync_state value by key."""
        cursor = self.conn.execute(
            "SELECT value FROM sync_state WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        return row["value"] if row else None

    def set_sync_state(self, key: str, value: str) -> None:
        """Set a sync_state value by key (upsert)."""
        self.conn.execute(
            """INSERT INTO sync_state (key, value)
               VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
        self.conn.commit()

    def delete_sync_state(self, key: str) -> None:
        """Delete a sync_state key."""
        self.conn.execute(
            "DELETE FROM sync_state WHERE key = ?",
            (key,),
        )
        self.conn.commit()

    # =========== Run Timeline (Context Graph v0) ===========

    def get_run_timeline(self, run_id: str) -> dict:
        """
        Get a unified timeline of all events/notes/verifications for a run.
        
        Returns:
            {
                "run": {...},
                "inputs": [...],
                "notes": [...],
                "verifications": [...],
                "events": [...],  # events with run_id in payload
            }
        """
        run = self.get_run_with_work_item(run_id) or self.get_run(run_id)
        if not run:
            return {"run": None, "inputs": [], "notes": [], "verifications": [], "events": []}

        inputs = self.list_run_inputs(run_id)

        # Get notes
        cursor = self.conn.execute(
            "SELECT * FROM run_notes WHERE run_id = ? ORDER BY created_at ASC",
            (run_id,),
        )
        notes = []
        for row in cursor.fetchall():
            note = dict(row)
            note["body"] = json.loads(note.get("body") or "{}")
            notes.append(note)

        # Get verifications
        cursor = self.conn.execute(
            "SELECT * FROM run_verifications WHERE run_id = ? ORDER BY created_at ASC",
            (run_id,),
        )
        verifications = []
        for row in cursor.fetchall():
            v = dict(row)
            v["attestation"] = json.loads(v.get("attestation") or "{}")
            verifications.append(v)

        # Get events that reference this run_id in their payload
        cursor = self.conn.execute(
            """SELECT * FROM events 
               WHERE json_extract(payload, '$.run_id') = ? 
               ORDER BY seq ASC""",
            (run_id,),
        )
        events = []
        for row in cursor.fetchall():
            event = dict(row)
            event["payload"] = json.loads(event.get("payload") or "{}")
            events.append(event)

        return {
            "run": run,
            "inputs": inputs,
            "notes": notes,
            "verifications": verifications,
            "events": events,
        }

    def get_run_notes(self, run_id: str) -> list[dict]:
        """Get all notes for a run, ordered by creation time."""
        cursor = self.conn.execute(
            "SELECT * FROM run_notes WHERE run_id = ? ORDER BY created_at ASC",
            (run_id,),
        )
        notes = []
        for row in cursor.fetchall():
            note = dict(row)
            note["body"] = json.loads(note.get("body") or "{}")
            notes.append(note)
        return notes

    # =========== Rollback State ===========

    def get_last_good_checkpoint(self) -> Optional[str]:
        """Get the last known-good checkpoint commit SHA."""
        return self.get_sync_state("last_good_checkpoint")

    def set_last_good_checkpoint(self,commit_sha: str) -> None:
        """Set the last known-good checkpoint commit SHA."""
        if commit_sha:
            self.set_sync_state("last_good_checkpoint", commit_sha)

    # =========== User Settings ==========

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a user setting by key."""
        cursor = self.conn.execute(
            "SELECT value FROM user_settings WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if row:
            return row["value"]
        return default

    def set_setting(self, key: str, value: str) -> None:
        """Set a user setting by key (upsert)."""
        self.conn.execute(
            """INSERT INTO user_settings (key, value, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')""",
            (key, value),
        )
        self.conn.commit()

    async def close_async(self):
        """Close database connection."""
        self.conn.close()

    def close(self):
        """Close the database connection."""
        self.conn.close()


EventStore = ProjectionStore

# Singleton instance
_store: Optional[ProjectionStore] = None
_stores_by_user: dict[str, ProjectionStore] = {}


def get_store(user_id: Optional[str] = None) -> ProjectionStore:
    """Get the projection store instance (optionally scoped to a user)."""
    global _store, _stores_by_user
    if user_id is None:
        if _store is None:
            _store = ProjectionStore()
        return _store
    if user_id not in _stores_by_user:
        _stores_by_user[user_id] = ProjectionStore(user_id=user_id)
    return _stores_by_user[user_id]
