"""Monitor de call do Teams — emite sinais Qt quando uma call começa/termina.

Encapsula um `QTimer` que periodicamente checa se o Teams está em call e
emite `call_started` / `call_ended` na borda de mudança de estado.

Heurística do MVP: "Teams rodando" conta como "em call". É grosseiro — música
ou o Teams aberto sem call disparam falso positivo. Combinar com energia de
áudio no loopback é refino pós-MVP (issue #9).
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from tt.detection.teams import is_teams_running


class CallMonitor(QObject):
    """Emite `call_started` / `call_ended` na borda de mudança de estado."""

    call_started = pyqtSignal()
    call_ended = pyqtSignal()

    def __init__(self, poll_interval_seconds: int = 5) -> None:
        super().__init__()
        self._in_call = False
        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_seconds * 1000)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        """Começa a checar periodicamente."""
        self._timer.start()

    def stop(self) -> None:
        """Para de checar."""
        self._timer.stop()

    def _poll(self) -> None:
        """Checagem periódica — disparada pelo QTimer."""
        self._update(in_call=is_teams_running())

    def _update(self, in_call: bool) -> None:
        """Aplica o novo estado e emite o sinal de borda correspondente.

        Separado de `_poll` para ser testável sem depender do `psutil` real.
        """
        if in_call and not self._in_call:
            self._in_call = True
            self.call_started.emit()
        elif not in_call and self._in_call:
            self._in_call = False
            self.call_ended.emit()
