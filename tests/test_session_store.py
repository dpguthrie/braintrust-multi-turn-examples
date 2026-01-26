import os

from src.backend.storage.session_store import SessionStore


def test_get_or_create_session_creates_row(tmp_path):
    db_path = tmp_path / "sessions.db"
    store = SessionStore(db_path=str(db_path))
    record = store.get_or_create_session("conv-1")
    assert record.conversation_id == "conv-1"
    assert record.root_span_id is None


def test_get_or_create_session_reuses_row(tmp_path):
    db_path = tmp_path / "sessions.db"
    store = SessionStore(db_path=str(db_path))
    first = store.get_or_create_session("conv-2")
    second = store.get_or_create_session("conv-2")
    assert first.conversation_id == second.conversation_id
    assert first.created_at == second.created_at
