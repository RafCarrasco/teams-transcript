"""Subpacote de detecção: descobre quando o Teams está numa call.

Combina dois sinais:

- `teams.py` — o processo do Teams está rodando? (via `psutil`)
- `call_state.py` — há áudio sustentado saindo pelo sistema? (heurística RMS)

Nenhum dos dois sozinho é conclusivo: o Teams pode estar aberto sem call, e
pode haver áudio do sistema sem ser do Teams. O orquestrador da aplicação
combina os sinais para decidir quando iniciar/parar a gravação.

Importar este pacote é leve — só depende de `psutil` e `numpy`, ambos no
conjunto base de dependências.
"""

from __future__ import annotations

from tt.detection.call_state import DEFAULT_RMS_THRESHOLD, is_in_call, rms
from tt.detection.teams import is_teams_running, teams_processes

__all__ = [
    "DEFAULT_RMS_THRESHOLD",
    "is_in_call",
    "rms",
    "is_teams_running",
    "teams_processes",
]
