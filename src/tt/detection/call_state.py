"""Heurística de "está em call" a partir do áudio de loopback — lógica pura.

A ideia: durante uma call do Teams, há áudio saindo continuamente pelos
alto-falantes (a voz dos outros participantes). Captando o loopback do
sistema (o que se ouve) e medindo a energia do sinal — a raiz quadrática
média, RMS — dá pra inferir, de forma barata, se "tem call rolando".

Isso é só um sinal, não uma certeza: música ou um vídeo no YouTube também
disparariam a heurística. A camada de detecção combina este sinal com a
checagem de processo do Teams (`tt.detection.teams`) para uma decisão mais
robusta.

Módulo de lógica pura: só `numpy`, sem hardware — totalmente testável.
"""

from __future__ import annotations

import numpy as np

# Limiar de RMS padrão acima do qual consideramos "tem áudio = provável call".
#
# Áudio float está em [-1, 1]. O silêncio digital tem RMS ~0; ruído de fundo
# fraco fica na casa de 1e-4..1e-3; fala/áudio de call costuma passar de 1e-2.
# 0.01 separa bem ruído de fundo de áudio real, com folga. Ajustável por
# chamada via parâmetro `threshold`.
DEFAULT_RMS_THRESHOLD = 0.01


def rms(samples: np.ndarray) -> float:
    """Raiz quadrática média (RMS) de um bloco de amostras de áudio.

    O RMS mede a energia/volume do sinal. Aceita entrada mono (1-D) ou
    multicanal (2-D) — neste caso todas as amostras entram no cálculo.
    Um array vazio devolve `0.0` (sem energia).
    """
    arr = np.asarray(samples, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    # float64 no cálculo evita perda de precisão ao somar muitos quadrados.
    return float(np.sqrt(np.mean(np.square(arr))))


def is_in_call(
    loopback_samples: np.ndarray,
    threshold: float = DEFAULT_RMS_THRESHOLD,
) -> bool:
    """Decide se há call em andamento a partir do áudio de loopback.

    Heurística: se o RMS do loopback atinge ou supera `threshold`, há
    energia de áudio sustentada saindo pelo sistema — provável call.

    O chamador deve passar um bloco representativo (p. ex. 0,5–1 s de
    áudio): blocos curtos demais pegam pausas naturais da fala e geram
    falsos negativos. Para robustez ainda maior, avalie vários blocos numa
    janela e exija que a maioria esteja acima do limiar.
    """
    return rms(loopback_samples) >= threshold
