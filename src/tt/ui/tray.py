"""Ícone de bandeja — menu e notificações nativas.

Roda de fundo enquanto o app espera por uma call. O menu dá acesso à pasta de
transcrições e a sair; `notify` mostra a notificação nativa quando um `.txt`
fica pronto.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon


class Tray(QSystemTrayIcon):
    """Ícone de bandeja com menu e notificações."""

    def __init__(self, output_dir: str | Path) -> None:
        super().__init__()
        self._output_dir = Path(output_dir)
        self.setIcon(QIcon())  # ícone default; arte do app é pós-MVP
        self.setToolTip("teams-transcript")

        self._menu = QMenu()
        self._open_action = QAction("Abrir pasta de transcrições", self._menu)
        self._open_action.triggered.connect(self._open_folder)
        self._quit_action = QAction("Sair", self._menu)
        self._menu.addAction(self._open_action)
        self._menu.addSeparator()
        self._menu.addAction(self._quit_action)
        self.setContextMenu(self._menu)

    def menu_actions(self) -> list[QAction]:
        """Ações do menu (usado em testes)."""
        return [self._open_action, self._quit_action]

    @property
    def quit_action(self) -> QAction:
        """Ação "Sair" — o app conecta isso ao encerramento."""
        return self._quit_action

    def notify(self, title: str, message: str) -> None:
        """Mostra uma notificação nativa do sistema."""
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information)

    def _open_folder(self) -> None:
        """Abre a pasta de transcrições no explorador de arquivos."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(self._output_dir)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(self._output_dir)], check=False)
        else:
            subprocess.run(["xdg-open", str(self._output_dir)], check=False)
