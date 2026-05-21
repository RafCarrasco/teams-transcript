"""Helpers de path — expansão, criação de diretórios e localização de dados.

Funções pequenas e cross-platform usadas pelo resto do pacote para lidar
com paths de forma consistente (expandir `~`, resolver para absoluto, etc.).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "teams-transcript"


def expand(path: str | os.PathLike[str]) -> Path:
    """Expande `~` e variáveis de ambiente e resolve para um Path absoluto.

    Não exige que o path exista — apenas normaliza. `resolve()` é usado com
    ``strict=False`` para que paths inexistentes ainda sejam normalizados.
    """
    raw = os.path.expandvars(os.fspath(path))
    return Path(raw).expanduser().resolve()


def ensure_dir(path: str | os.PathLike[str]) -> Path:
    """Garante que o diretório exista (criando pais se preciso) e o retorna.

    Idempotente: chamar num diretório já existente não levanta erro.
    """
    target = expand(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def app_data_dir() -> Path:
    """Diretório padrão de dados da app, dependente da plataforma.

    - Windows: ``%LOCALAPPDATA%/teams-transcript``
    - macOS:   ``~/Library/Application Support/teams-transcript``
    - Linux:   ``$XDG_DATA_HOME/teams-transcript`` (default ``~/.local/share``)

    O diretório não é criado aqui — use :func:`ensure_dir` se precisar dele
    materializado.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or "~/AppData/Local"
    elif sys.platform == "darwin":
        base = "~/Library/Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or "~/.local/share"
    return expand(base) / APP_NAME
