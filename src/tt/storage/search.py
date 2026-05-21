"""Busca full-text em transcrições via FTS5.

O conteúdo das transcrições vive na tabela virtual `transcript_fts`
(colunas `meeting_id` e `content`). `index_meeting` mantém esse índice;
`search_meetings` consulta e devolve resultados rankeados por `bm25()`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from tt.storage.db import get_connection, init_db

# Local padrão do banco quando a CLI chama search_meetings(query) sem
# passar db_path explícito.
DEFAULT_DB_PATH = Path.home() / ".teams-transcript" / "tt.db"


def index_meeting(conn: sqlite3.Connection, meeting_id: str, content: str) -> None:
    """Insere ou atualiza o texto indexado de uma reunião no FTS.

    FTS5 (sem `content=`) não suporta UPDATE direto de forma confiável,
    então removemos qualquer entrada anterior daquele `meeting_id` e
    reinserimos — mantendo o índice consistente quando a transcrição é
    reprocessada.
    """
    conn.execute("DELETE FROM transcript_fts WHERE meeting_id = ?", (meeting_id,))
    conn.execute(
        "INSERT INTO transcript_fts (meeting_id, content) VALUES (?, ?)",
        (meeting_id, content),
    )


def search_meetings(
    query: str,
    db_path: str | Path | None = None,
) -> list[dict]:
    """Busca `query` nas transcrições indexadas.

    Retorna uma lista de dicts ordenada por relevância (mais relevante
    primeiro), cada um com:
        - `meeting_id`: id da reunião
        - `snippet`: trecho do conteúdo com o termo destacado entre `[...]`
        - `rank`: score bruto do bm25 (menor = mais relevante)

    `db_path` é opcional; com default em `~/.teams-transcript/tt.db` para
    a chamada simples `search_meetings(query)` feita pela CLI.
    """
    if not query or not query.strip():
        return []

    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    conn = get_connection(path)
    try:
        init_db(conn)
        try:
            rows = conn.execute(
                """
                SELECT
                    meeting_id,
                    snippet(transcript_fts, 1, '[', ']', ' … ', 12) AS snippet,
                    bm25(transcript_fts) AS rank
                FROM transcript_fts
                WHERE transcript_fts MATCH ?
                ORDER BY rank
                """,
                (query,),
            ).fetchall()
        except sqlite3.OperationalError:
            # Query FTS malformada (ex.: operadores soltos) -> sem resultados.
            return []
        return [
            {"meeting_id": r["meeting_id"], "snippet": r["snippet"], "rank": r["rank"]}
            for r in rows
        ]
    finally:
        conn.close()
