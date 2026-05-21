"""Conexão SQLite, criação de schema e migrations.

O banco guarda metadados de reuniões (`meetings`) e um índice full-text
(`transcript_fts`, FTS5) para busca em transcrições.

O versionamento de schema usa o pragma `user_version` do SQLite. Cada
migration é uma função idempotente registrada em `_MIGRATIONS`; `init_db`
aplica em ordem todas as migrations ainda não aplicadas. Para evoluir o
schema no futuro, basta adicionar uma nova função ao final da lista.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Versão de schema esperada = número de migrations registradas.
# Não alterar manualmente: deriva de len(_MIGRATIONS).


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Abre (criando se preciso) uma conexão SQLite para `db_path`.

    Cria o diretório pai caso não exista, ativa `PRAGMA foreign_keys` e
    define `row_factory = sqlite3.Row` para acesso por nome de coluna.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def schema_version(conn: sqlite3.Connection) -> int:
    """Versão de schema atual do banco (pragma `user_version`)."""
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _migration_001_initial(conn: sqlite3.Connection) -> None:
    """Schema inicial: tabela `meetings` + tabela virtual FTS5."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id TEXT PRIMARY KEY,
            started_at TIMESTAMP,
            duration_seconds INTEGER,
            title TEXT,
            transcript_path TEXT,
            audio_path TEXT,
            has_summary BOOLEAN,
            metadata JSON
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS transcript_fts
        USING fts5(meeting_id, content)
        """
    )


# Lista ordenada de migrations. O índice (1-based) é a versão de schema
# que a migration produz. Nunca remover nem reordenar entradas existentes;
# apenas anexar novas ao final.
_MIGRATIONS = [
    _migration_001_initial,
]

SCHEMA_VERSION = len(_MIGRATIONS)


def init_db(conn: sqlite3.Connection) -> None:
    """Aplica todas as migrations pendentes. Idempotente.

    Roda apenas as migrations cuja versão é maior que a `user_version`
    atual do banco, então chamar mais de uma vez é seguro.
    """
    current = schema_version(conn)
    for index, migration in enumerate(_MIGRATIONS, start=1):
        if index > current:
            migration(conn)
            conn.execute(f"PRAGMA user_version = {index}")
    conn.commit()
