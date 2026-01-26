import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class SessionRecord:
    conversation_id: str
    root_span_id: str | None
    root_span_export: str | None
    thread_id: str | None
    document_path: str | None
    transcript: list[dict]
    created_at: str


class SessionStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv("SESSION_DB_PATH", "./data/sessions.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    conversation_id TEXT PRIMARY KEY,
                    root_span_id TEXT,
                    root_span_export TEXT,
                    thread_id TEXT,
                    document_path TEXT,
                    transcript_json TEXT,
                    created_at TEXT
                )
                """
            )
            conn.commit()
            self._ensure_columns(conn)

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        cursor = conn.execute("PRAGMA table_info(sessions)")
        columns = {row[1] for row in cursor.fetchall()}
        if "transcript_json" not in columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN transcript_json TEXT")
        if "document_path" not in columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN document_path TEXT")
        conn.commit()

    def get_or_create_session(self, conversation_id: str) -> SessionRecord:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT conversation_id, root_span_id, root_span_export, thread_id, document_path, transcript_json, created_at "
                "FROM sessions WHERE conversation_id = ?",
                (conversation_id,),
            )
            row = cursor.fetchone()
            if row:
                transcript_raw = row[5] or "[]"
                transcript = json.loads(transcript_raw)
                return SessionRecord(row[0], row[1], row[2], row[3], row[4], transcript, row[6])

            created_at = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO sessions (conversation_id, root_span_id, root_span_export, thread_id, document_path, transcript_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (conversation_id, None, None, None, None, "[]", created_at),
            )
            conn.commit()
            return SessionRecord(conversation_id, None, None, None, None, [], created_at)

    def update_root_span(
        self,
        conversation_id: str,
        root_span_id: str,
        root_span_export: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET root_span_id = ?, root_span_export = ? "
                "WHERE conversation_id = ?",
                (root_span_id, root_span_export, conversation_id),
            )
            conn.commit()

    def update_thread_id(self, conversation_id: str, thread_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET thread_id = ? WHERE conversation_id = ?",
                (thread_id, conversation_id),
            )
            conn.commit()

    def update_document_path(self, conversation_id: str, document_path: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET document_path = ? WHERE conversation_id = ?",
                (document_path, conversation_id),
            )
            conn.commit()

    def update_transcript(self, conversation_id: str, transcript: list[dict]) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET transcript_json = ? WHERE conversation_id = ?",
                (json.dumps(transcript), conversation_id),
            )
            conn.commit()
