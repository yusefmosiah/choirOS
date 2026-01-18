"""Auth gateway stub: passkey-friendly flows + session store."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, Optional

def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


DEFAULT_AUTH_DB = _project_root() / ".context" / "auth.sqlite"
DEFAULT_RP_ID = os.environ.get("CHOIROS_RP_ID", "localhost")


@dataclass(frozen=True)
class AuthSession:
    session_id: str
    user_id: str
    created_at: str
    last_seen_at: str
    client_label: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
            "client_label": self.client_label,
        }


@dataclass(frozen=True)
class PasskeyRecord:
    credential_id: str
    user_id: str
    created_at: str

    def to_dict(self) -> dict:
        return {
            "credential_id": self.credential_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ChallengeRecord:
    challenge_id: str
    user_id: str
    kind: str
    challenge: str
    rp_id: str
    expires_at: str

    def to_dict(self) -> dict:
        return {
            "challenge_id": self.challenge_id,
            "user_id": self.user_id,
            "kind": self.kind,
            "challenge": self.challenge,
            "rp_id": self.rp_id,
            "expires_at": self.expires_at,
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def extract_session_token(headers: Mapping[str, str]) -> Optional[str]:
    auth_header = headers.get("authorization") or headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    token = headers.get("x-choir-session") or headers.get("X-Choir-Session")
    if token:
        return token.strip()
    return None


class AuthStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = DEFAULT_AUTH_DB
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_passkeys (
                credential_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                public_key TEXT,
                transports TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES auth_users(user_id)
            );

            CREATE TABLE IF NOT EXISTS auth_challenges (
                challenge_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                challenge TEXT NOT NULL,
                rp_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS auth_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                client_label TEXT,
                revoked_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
                ON auth_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_auth_passkeys_user
                ON auth_passkeys(user_id);
            CREATE INDEX IF NOT EXISTS idx_auth_challenges_user
                ON auth_challenges(user_id);
            """
        )
        self.conn.commit()

    def ensure_user(self, user_id: str, username: Optional[str] = None, display_name: Optional[str] = None) -> None:
        existing = self.conn.execute(
            "SELECT user_id FROM auth_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if existing:
            return
        self.conn.execute(
            "INSERT INTO auth_users (user_id, username, display_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, display_name, _iso_now()),
        )
        self.conn.commit()

    def list_passkeys(self, user_id: str) -> list[PasskeyRecord]:
        rows = self.conn.execute(
            "SELECT credential_id, user_id, created_at FROM auth_passkeys WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [PasskeyRecord(**dict(row)) for row in rows]

    def register_passkey(
        self,
        user_id: str,
        credential_id: str,
        public_key: Optional[str] = None,
        transports: Optional[str] = None,
    ) -> PasskeyRecord:
        self.ensure_user(user_id)
        created_at = _iso_now()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO auth_passkeys
                (credential_id, user_id, public_key, transports, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (credential_id, user_id, public_key, transports, created_at),
        )
        self.conn.commit()
        return PasskeyRecord(credential_id=credential_id, user_id=user_id, created_at=created_at)

    def create_challenge(self, user_id: str, kind: str, rp_id: Optional[str] = None) -> ChallengeRecord:
        rp = rp_id or DEFAULT_RP_ID
        challenge_id = str(uuid.uuid4())
        challenge = _b64url(secrets.token_bytes(32))
        created_at = _utc_now()
        expires_at = created_at + timedelta(minutes=10)
        self.conn.execute(
            """
            INSERT INTO auth_challenges
                (challenge_id, user_id, kind, challenge, rp_id, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                challenge_id,
                user_id,
                kind,
                challenge,
                rp,
                created_at.isoformat().replace("+00:00", "Z"),
                expires_at.isoformat().replace("+00:00", "Z"),
            ),
        )
        self.conn.commit()
        return ChallengeRecord(
            challenge_id=challenge_id,
            user_id=user_id,
            kind=kind,
            challenge=challenge,
            rp_id=rp,
            expires_at=expires_at.isoformat().replace("+00:00", "Z"),
        )

    def consume_challenge(self, challenge_id: str, expected_kind: str) -> Optional[ChallengeRecord]:
        row = self.conn.execute(
            """
            SELECT challenge_id, user_id, kind, challenge, rp_id, expires_at, consumed_at
            FROM auth_challenges
            WHERE challenge_id = ?
            """,
            (challenge_id,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("consumed_at"):
            return None
        if data.get("kind") != expected_kind:
            return None
        expires_at = data.get("expires_at")
        if expires_at and datetime.fromisoformat(expires_at.replace("Z", "+00:00")) < _utc_now():
            return None
        consumed_at = _iso_now()
        self.conn.execute(
            "UPDATE auth_challenges SET consumed_at = ? WHERE challenge_id = ?",
            (consumed_at, challenge_id),
        )
        self.conn.commit()
        return ChallengeRecord(
            challenge_id=data["challenge_id"],
            user_id=data["user_id"],
            kind=data["kind"],
            challenge=data["challenge"],
            rp_id=data["rp_id"],
            expires_at=data["expires_at"],
        )

    def create_session(self, user_id: str, client_label: Optional[str] = None) -> tuple[AuthSession, str]:
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        session_id = str(uuid.uuid4())
        now = _iso_now()
        self.conn.execute(
            """
            INSERT INTO auth_sessions
                (session_id, user_id, token_hash, created_at, last_seen_at, client_label)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, token_hash, now, now, client_label),
        )
        self.conn.commit()
        return AuthSession(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_seen_at=now,
            client_label=client_label,
        ), token

    def verify_session(self, token: str) -> Optional[AuthSession]:
        token_hash = _hash_token(token)
        row = self.conn.execute(
            """
            SELECT session_id, user_id, created_at, last_seen_at, client_label, revoked_at
            FROM auth_sessions
            WHERE token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("revoked_at"):
            return None
        now = _iso_now()
        self.conn.execute(
            "UPDATE auth_sessions SET last_seen_at = ? WHERE session_id = ?",
            (now, data["session_id"]),
        )
        self.conn.commit()
        return AuthSession(
            session_id=data["session_id"],
            user_id=data["user_id"],
            created_at=data["created_at"],
            last_seen_at=now,
            client_label=data.get("client_label"),
        )

    def list_sessions(self, user_id: str) -> list[AuthSession]:
        rows = self.conn.execute(
            """
            SELECT session_id, user_id, created_at, last_seen_at, client_label
            FROM auth_sessions
            WHERE user_id = ? AND revoked_at IS NULL
            ORDER BY last_seen_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [AuthSession(**dict(row)) for row in rows]

    def revoke_session(self, user_id: str, session_id: str) -> bool:
        row = self.conn.execute(
            "SELECT session_id FROM auth_sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not row:
            return False
        self.conn.execute(
            "UPDATE auth_sessions SET revoked_at = ? WHERE session_id = ?",
            (_iso_now(), session_id),
        )
        self.conn.commit()
        return True


_store: Optional[AuthStore] = None


def get_auth_store() -> AuthStore:
    global _store
    if _store is None:
        _store = AuthStore()
    return _store


def build_webauthn_user_handle(user_id: str) -> str:
    return _b64url(user_id.encode())


def build_webauthn_challenge(challenge: str) -> str:
    return challenge
