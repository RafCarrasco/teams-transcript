"""Testes do CRUD de reuniões."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from tt.storage.db import get_connection, init_db
from tt.storage.meetings import (
    Meeting,
    create_meeting,
    delete_meeting,
    get_meeting,
    list_meetings,
    update_meeting,
)


@pytest.fixture
def conn(tmp_path):
    c = get_connection(tmp_path / "tt.db")
    init_db(c)
    yield c
    c.close()


def test_create_generates_id(conn):
    m = create_meeting(conn, Meeting(title="Sync semanal"))
    assert m.id
    assert len(m.id) == 36  # uuid4 com hifens


def test_create_respects_given_id(conn):
    m = create_meeting(conn, Meeting(id="fixed-id", title="X"))
    assert m.id == "fixed-id"


def test_crud_round_trip_with_metadata(conn):
    started = datetime(2026, 5, 21, 14, 30, 0)
    meta = {"vendor": "ACME", "tags": ["quote", "urgente"], "score": 9}
    created = create_meeting(
        conn,
        Meeting(
            started_at=started,
            duration_seconds=1800,
            title="Revisão de quote",
            transcript_path="/tmp/t.md",
            audio_path="/tmp/t.wav",
            has_summary=True,
            metadata=meta,
        ),
    )
    fetched = get_meeting(conn, created.id)
    assert fetched is not None
    assert fetched.title == "Revisão de quote"
    assert fetched.duration_seconds == 1800
    assert fetched.started_at == started
    assert fetched.transcript_path == "/tmp/t.md"
    assert fetched.audio_path == "/tmp/t.wav"
    assert fetched.has_summary is True
    assert fetched.metadata == meta  # dict round-trip via JSON


def test_has_summary_is_real_bool(conn):
    m = create_meeting(conn, Meeting(title="A", has_summary=False))
    fetched = get_meeting(conn, m.id)
    assert fetched.has_summary is False
    assert isinstance(fetched.has_summary, bool)


def test_get_missing_returns_none(conn):
    assert get_meeting(conn, "nao-existe") is None


def test_metadata_defaults_to_empty_dict(conn):
    m = create_meeting(conn, Meeting(title="Sem meta"))
    fetched = get_meeting(conn, m.id)
    assert fetched.metadata == {}


def test_list_meetings_orders_by_started_at_desc(conn):
    base = datetime(2026, 5, 1, 9, 0, 0)
    create_meeting(conn, Meeting(title="antiga", started_at=base))
    create_meeting(conn, Meeting(title="recente", started_at=base + timedelta(days=10)))
    create_meeting(conn, Meeting(title="meio", started_at=base + timedelta(days=5)))
    titles = [m.title for m in list_meetings(conn)]
    assert titles == ["recente", "meio", "antiga"]


def test_list_meetings_pagination(conn):
    base = datetime(2026, 5, 1, 9, 0, 0)
    for i in range(5):
        create_meeting(conn, Meeting(title=f"m{i}", started_at=base + timedelta(days=i)))
    page = list_meetings(conn, limit=2, offset=0)
    assert [m.title for m in page] == ["m4", "m3"]
    page2 = list_meetings(conn, limit=2, offset=2)
    assert [m.title for m in page2] == ["m2", "m1"]


def test_update_meeting(conn):
    m = create_meeting(conn, Meeting(title="rascunho", has_summary=False))
    m.title = "final"
    m.has_summary = True
    m.metadata = {"revisado": True}
    update_meeting(conn, m)
    fetched = get_meeting(conn, m.id)
    assert fetched.title == "final"
    assert fetched.has_summary is True
    assert fetched.metadata == {"revisado": True}


def test_delete_meeting(conn):
    m = create_meeting(conn, Meeting(title="apagar"))
    delete_meeting(conn, m.id)
    assert get_meeting(conn, m.id) is None
    assert list_meetings(conn) == []
