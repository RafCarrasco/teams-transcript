"""Detecção do processo do Microsoft Teams via `psutil`.

Existem duas gerações do app desktop, com nomes de executável distintos:

- Teams clássico (Electron):  `Teams.exe`
- novo Teams (WebView2):      `ms-teams.exe`

Comparamos por nome em minúsculas, então variações de capitalização do
sistema de arquivos não atrapalham. `psutil` está no conjunto base de
dependências, então este módulo importa e roda em qualquer ambiente — e é
testável mockando `psutil.process_iter`.
"""

from __future__ import annotations

import psutil

# Nomes de executável do Teams (clássico e novo), em minúsculas para
# comparação case-insensitive.
_TEAMS_PROCESS_NAMES = frozenset({"teams.exe", "ms-teams.exe"})


def teams_processes() -> list[psutil.Process]:
    """Lista os processos do Teams atualmente em execução.

    Devolve uma lista de `psutil.Process` cujo nome bate com um executável
    conhecido do Teams. Lista vazia significa que o Teams não está rodando.

    Processos que terminam ou ficam inacessíveis durante a varredura são
    ignorados em silêncio — uma condição de corrida normal ao iterar sobre
    processos vivos.
    """
    found: list[psutil.Process] = []
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info.get("name")
            if name and name.lower() in _TEAMS_PROCESS_NAMES:
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # O processo morreu ou ficou inacessível entre listar e ler — ignora.
            continue
    return found


def is_teams_running() -> bool:
    """`True` se há ao menos um processo do Teams em execução.

    Atenção: o Teams estar aberto não significa que há uma call ativa —
    combine com `tt.detection.call_state.is_in_call` para isso.
    """
    return len(teams_processes()) > 0
