"""Persistência: SQLite + FTS5 + CRUD de meetings.

Camada de armazenamento do teams-transcript. Guarda metadados de reuniões
numa tabela `meetings` e indexa o texto das transcrições numa tabela
virtual FTS5 (`transcript_fts`) para busca full-text.

Módulos:
    db        conexão SQLite, criação de schema e migrations
    meetings  dataclass Meeting + CRUD
    search    indexação e busca full-text

Uso típico::

    from tt.storage import get_connection, init_db, Meeting, create_meeting

    conn = get_connection("~/.teams-transcript/tt.db")
    init_db(conn)
    meeting = create_meeting(conn, Meeting(title="Sync"))
"""

from __future__ import annotations

from tt.storage.db import (
    SCHEMA_VERSION,
    get_connection,
    init_db,
    schema_version,
)
from tt.storage.meetings import (
    Meeting,
    create_meeting,
    delete_meeting,
    get_meeting,
    list_meetings,
    update_meeting,
)
from tt.storage.search import index_meeting, search_meetings

__all__ = [
    "SCHEMA_VERSION",
    "get_connection",
    "init_db",
    "schema_version",
    "Meeting",
    "create_meeting",
    "get_meeting",
    "list_meetings",
    "update_meeting",
    "delete_meeting",
    "index_meeting",
    "search_meetings",
]
