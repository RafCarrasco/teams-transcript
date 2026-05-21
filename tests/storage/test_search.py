"""Testes da busca full-text via FTS5."""

from __future__ import annotations

import pytest

from tt.storage.db import get_connection, init_db
from tt.storage.meetings import Meeting, create_meeting, delete_meeting
from tt.storage.search import index_meeting, search_meetings


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "tt.db"


@pytest.fixture
def conn(db_path):
    c = get_connection(db_path)
    init_db(c)
    yield c
    c.close()


def test_index_and_search_returns_hit(conn, db_path):
    m = create_meeting(conn, Meeting(title="Reunião vendor"))
    index_meeting(conn, m.id, "Discutimos o contrato com o vendor ACME hoje.")
    conn.commit()
    results = search_meetings("vendor", db_path=db_path)
    assert len(results) == 1
    assert results[0]["meeting_id"] == m.id
    assert "snippet" in results[0]


def test_search_empty_when_no_match(conn, db_path):
    m = create_meeting(conn, Meeting(title="Reunião"))
    index_meeting(conn, m.id, "Nada relevante aqui.")
    conn.commit()
    assert search_meetings("inexistente", db_path=db_path) == []


def test_search_ranks_by_relevance(conn, db_path):
    m1 = create_meeting(conn, Meeting(title="Pouco"))
    m2 = create_meeting(conn, Meeting(title="Muito"))
    m3 = create_meeting(conn, Meeting(title="Nada"))
    index_meeting(conn, m1.id, "orçamento mencionado uma vez no fim.")
    index_meeting(
        conn,
        m2.id,
        "orçamento orçamento orçamento revisar orçamento aprovar orçamento.",
    )
    index_meeting(conn, m3.id, "assunto totalmente diferente sem o termo.")
    conn.commit()
    results = search_meetings("orçamento", db_path=db_path)
    ids = [r["meeting_id"] for r in results]
    assert set(ids) == {m1.id, m2.id}
    # m2 tem mais ocorrências -> deve rankear primeiro
    assert ids[0] == m2.id


def test_snippet_contains_term(conn, db_path):
    m = create_meeting(conn, Meeting(title="X"))
    index_meeting(conn, m.id, "uma frase longa antes do termo importante e depois mais texto.")
    conn.commit()
    results = search_meetings("importante", db_path=db_path)
    assert len(results) == 1
    assert "importante" in results[0]["snippet"].lower()


def test_index_meeting_updates_existing_content(conn, db_path):
    m = create_meeting(conn, Meeting(title="X"))
    index_meeting(conn, m.id, "conteudo antigo obsoleto")
    conn.commit()
    index_meeting(conn, m.id, "conteudo novo atualizado")
    conn.commit()
    assert search_meetings("obsoleto", db_path=db_path) == []
    assert len(search_meetings("atualizado", db_path=db_path)) == 1


def test_delete_meeting_removes_from_fts(conn, db_path):
    m = create_meeting(conn, Meeting(title="apagar"))
    index_meeting(conn, m.id, "termo unico procuravel")
    conn.commit()
    assert len(search_meetings("procuravel", db_path=db_path)) == 1
    delete_meeting(conn, m.id)
    conn.commit()
    assert search_meetings("procuravel", db_path=db_path) == []
