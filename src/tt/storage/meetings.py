"""CRUD de reuniões na tabela `meetings`.

A `Meeting` é uma dataclass que espelha as colunas da tabela. A coluna
`metadata` é serializada para/de JSON automaticamente, então no Python ela
é sempre um `dict`. `has_summary` é exposto como `bool` real (o SQLite
armazena 0/1).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime

# Ordem fixa das colunas — usada em INSERT/UPDATE/SELECT.
_COLUMNS = (
    "id",
    "started_at",
    "duration_seconds",
    "title",
    "transcript_path",
    "audio_path",
    "has_summary",
    "metadata",
)


@dataclass
class Meeting:
    """Uma reunião transcrita. Espelha a tabela `meetings`."""

    id: str | None = None
    started_at: datetime | None = None
    duration_seconds: int | None = None
    title: str | None = None
    transcript_path: str | None = None
    audio_path: str | None = None
    has_summary: bool = False
    metadata: dict = field(default_factory=dict)


def _to_row(meeting: Meeting) -> dict:
    """Converte uma `Meeting` no dict de valores para o SQLite."""
    return {
        "id": meeting.id,
        "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
        "duration_seconds": meeting.duration_seconds,
        "title": meeting.title,
        "transcript_path": meeting.transcript_path,
        "audio_path": meeting.audio_path,
        "has_summary": 1 if meeting.has_summary else 0,
        "metadata": json.dumps(meeting.metadata or {}),
    }


def _from_row(row: sqlite3.Row) -> Meeting:
    """Reconstrói uma `Meeting` a partir de uma linha do banco."""
    started_at = row["started_at"]
    raw_meta = row["metadata"]
    return Meeting(
        id=row["id"],
        started_at=datetime.fromisoformat(started_at) if started_at else None,
        duration_seconds=row["duration_seconds"],
        title=row["title"],
        transcript_path=row["transcript_path"],
        audio_path=row["audio_path"],
        has_summary=bool(row["has_summary"]),
        metadata=json.loads(raw_meta) if raw_meta else {},
    )


def create_meeting(conn: sqlite3.Connection, meeting: Meeting) -> Meeting:
    """Insere uma reunião. Gera um `id` (uuid4) se não fornecido.

    Retorna a `Meeting` com o `id` definitivo preenchido.
    """
    if not meeting.id:
        meeting.id = str(uuid.uuid4())
    row = _to_row(meeting)
    placeholders = ", ".join(f":{c}" for c in _COLUMNS)
    conn.execute(
        f"INSERT INTO meetings ({', '.join(_COLUMNS)}) VALUES ({placeholders})",
        row,
    )
    conn.commit()
    return meeting


def get_meeting(conn: sqlite3.Connection, meeting_id: str) -> Meeting | None:
    """Busca uma reunião pelo `id`. Retorna `None` se não existir."""
    row = conn.execute(
        "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
    ).fetchone()
    return _from_row(row) if row is not None else None


def list_meetings(
    conn: sqlite3.Connection,
    limit: int | None = None,
    offset: int = 0,
) -> list[Meeting]:
    """Lista reuniões ordenadas por `started_at` desc (mais recente primeiro).

    Paginação opcional via `limit`/`offset`. `NULL` em `started_at` vai
    para o final da lista.
    """
    sql = "SELECT * FROM meetings ORDER BY started_at IS NULL, started_at DESC"
    params: list[object] = []
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend((limit, offset))
    elif offset:
        # OFFSET sem LIMIT não é válido em SQLite; usa LIMIT -1 (sem teto).
        sql += " LIMIT -1 OFFSET ?"
        params.append(offset)
    rows = conn.execute(sql, params).fetchall()
    return [_from_row(r) for r in rows]


def update_meeting(conn: sqlite3.Connection, meeting: Meeting) -> None:
    """Atualiza todas as colunas de uma reunião existente (identificada pelo `id`)."""
    if not meeting.id:
        raise ValueError("update_meeting requer uma Meeting com id definido")
    row = _to_row(meeting)
    assignments = ", ".join(f"{c} = :{c}" for c in _COLUMNS if c != "id")
    conn.execute(f"UPDATE meetings SET {assignments} WHERE id = :id", row)
    conn.commit()


def delete_meeting(conn: sqlite3.Connection, meeting_id: str) -> None:
    """Remove uma reunião e o conteúdo indexado dela no FTS."""
    conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
    conn.execute("DELETE FROM transcript_fts WHERE meeting_id = ?", (meeting_id,))
    conn.commit()
