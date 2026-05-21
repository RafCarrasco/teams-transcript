"""Testes da conexão SQLite, criação de schema e migrations."""

from __future__ import annotations

import sqlite3

from tt.storage.db import get_connection, init_db, schema_version


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table')"
    ).fetchall()
    return {r["name"] for r in rows}


def test_get_connection_creates_parent_dir(tmp_path):
    db_path = tmp_path / "nested" / "deep" / "tt.db"
    conn = get_connection(db_path)
    try:
        assert db_path.parent.is_dir()
        assert isinstance(conn, sqlite3.Connection)
    finally:
        conn.close()


def test_get_connection_uses_row_factory(tmp_path):
    conn = get_connection(tmp_path / "tt.db")
    try:
        assert conn.row_factory is sqlite3.Row
    finally:
        conn.close()


def test_get_connection_enables_foreign_keys(tmp_path):
    conn = get_connection(tmp_path / "tt.db")
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_init_db_creates_tables(tmp_path):
    conn = get_connection(tmp_path / "tt.db")
    try:
        init_db(conn)
        names = _table_names(conn)
        assert "meetings" in names
        assert "transcript_fts" in names
    finally:
        conn.close()


def test_init_db_is_idempotent(tmp_path):
    conn = get_connection(tmp_path / "tt.db")
    try:
        init_db(conn)
        # rodar de novo não deve levantar exceção
        init_db(conn)
        init_db(conn)
        assert "meetings" in _table_names(conn)
    finally:
        conn.close()


def test_schema_version_set_after_init(tmp_path):
    conn = get_connection(tmp_path / "tt.db")
    try:
        assert schema_version(conn) == 0
        init_db(conn)
        assert schema_version(conn) >= 1
    finally:
        conn.close()
