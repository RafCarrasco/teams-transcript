"""Máquina de estados do app — lógica pura, sem Qt.

Isolada para ser testável sem GUI. `App` (em app.py) instancia uma
`StateMachine` e reage às mudanças de `state`.

Ciclo de vida::

    IDLE ──call detectada──> CALL_DETECTED ──clique REC──> RECORDING
      ^                            │                          │
      │                       call sumiu                 clique STOP
      │                            v                     (ou call acabou)
      └────────────────────────  IDLE                         v
      │                                                  TRANSCRIBING
      └────────────── transcrição terminou ◄──────────────────┘
"""

from __future__ import annotations

from enum import Enum, auto


class AppState(Enum):
    """Estados possíveis do app."""

    IDLE = auto()           # sem call
    CALL_DETECTED = auto()  # call do Teams detectada; botão visível
    RECORDING = auto()      # gravando áudio
    TRANSCRIBING = auto()   # Whisper rodando pós-call


class StateMachine:
    """Transições válidas do ciclo de vida do app.

    Transições inválidas (ex.: REC sem call detectada) são ignoradas — o
    estado simplesmente não muda. Assim a UI pode disparar eventos sem se
    preocupar em validar a ordem.
    """

    def __init__(self) -> None:
        self.state = AppState.IDLE

    def on_call_started(self) -> None:
        """Teams entrou em call."""
        if self.state is AppState.IDLE:
            self.state = AppState.CALL_DETECTED

    def on_call_ended(self) -> None:
        """Teams saiu da call."""
        if self.state is AppState.CALL_DETECTED:
            self.state = AppState.IDLE
        elif self.state is AppState.RECORDING:
            # Call acabou no meio da gravação -> para e transcreve.
            self.state = AppState.TRANSCRIBING

    def on_rec_clicked(self) -> None:
        """Usuário clicou REC."""
        if self.state is AppState.CALL_DETECTED:
            self.state = AppState.RECORDING

    def on_stop_clicked(self) -> None:
        """Usuário clicou STOP."""
        if self.state is AppState.RECORDING:
            self.state = AppState.TRANSCRIBING

    def on_transcription_done(self) -> None:
        """A transcrição pós-call terminou (com sucesso ou erro)."""
        if self.state is AppState.TRANSCRIBING:
            self.state = AppState.IDLE
