"""Testes dos helpers de path (`tt.utils.paths`)."""

from __future__ import annotations

from pathlib import Path

from tt.utils.paths import app_data_dir, ensure_dir, expand


def test_expand_resolves_tilde(monkeypatch, tmp_path):
    """`expand` deve trocar `~` pelo home do usuário e resolver para absoluto."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    result = expand("~/algum/arquivo.txt")

    assert result.is_absolute()
    assert "~" not in str(result)
    assert result == (tmp_path / "algum" / "arquivo.txt").resolve()


def test_expand_accepts_path_object(tmp_path):
    """`expand` aceita tanto str quanto Path."""
    result = expand(tmp_path / "sub" / ".." / "x")
    assert result == (tmp_path / "x").resolve()


def test_ensure_dir_creates_directory(tmp_path):
    """`ensure_dir` cria o diretório (e pais) e o retorna."""
    target = tmp_path / "a" / "b" / "c"
    assert not target.exists()

    result = ensure_dir(target)

    assert result == target.resolve()
    assert target.is_dir()


def test_ensure_dir_idempotent(tmp_path):
    """Chamar `ensure_dir` num diretório já existente não quebra."""
    target = tmp_path / "existe"
    target.mkdir()

    result = ensure_dir(target)

    assert result.is_dir()


def test_app_data_dir_is_absolute_path():
    """`app_data_dir` retorna um Path absoluto contendo o nome da app."""
    result = app_data_dir()
    assert isinstance(result, Path)
    assert result.is_absolute()
    assert "teams-transcript" in str(result)
