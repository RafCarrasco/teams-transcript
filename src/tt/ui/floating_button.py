"""Botão flutuante — janela frameless, always-on-top, arrastável.

Aparece quando uma call do Teams é detectada. Não é embutido no Teams: é uma
janela própria que flutua por cima de tudo (como a barra de um gravador de
tela). Mostra REC / STOP+tempo / "Transcrevendo…" e emite `rec_clicked` /
`stop_clicked`.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QPushButton, QWidget


class FloatingButton(QWidget):
    """Janelinha com um botão que muda conforme o estado do app."""

    rec_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        # Frameless + sempre no topo + Tool (não aparece na barra de tarefas).
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self._button = QPushButton(self)
        self._button.clicked.connect(self._on_click)
        self._state = "idle"
        self._drag_offset = None
        self.resize(170, 48)
        self.set_state("idle")

    def label(self) -> str:
        """Texto atual do botão (usado em testes e logs)."""
        return self._button.text()

    def set_state(self, state: str, elapsed: str = "") -> None:
        """Atualiza o rótulo conforme o estado.

        Args:
            state: ``idle`` (pronto para gravar), ``recording`` (gravando) ou
                ``transcribing`` (transcrição em andamento).
            elapsed: tempo decorrido ``MM:SS``, mostrado no estado recording.
        """
        self._state = state
        if state == "idle":
            self._button.setText("●  REC")
        elif state == "recording":
            self._button.setText(f"■  STOP   {elapsed}")
        elif state == "transcribing":
            self._button.setText("Transcrevendo…  ⏳")
        self._button.resize(self.size())

    def _on_click(self) -> None:
        if self._state == "idle":
            self.rec_clicked.emit()
        elif self._state == "recording":
            self.stop_clicked.emit()
        # estado 'transcribing' -> clique ignorado.

    # --- arraste da janela (frameless não tem barra de título) ------------
    def mousePressEvent(self, event):  # noqa: ANN001, N802 - override do Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):  # noqa: ANN001, N802 - override do Qt
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):  # noqa: ANN001, N802 - override do Qt
        self._drag_offset = None
