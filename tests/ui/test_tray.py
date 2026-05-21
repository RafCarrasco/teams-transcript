"""Testes do ícone de bandeja."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from tt.ui.tray import Tray  # noqa: E402

_app = QApplication.instance() or QApplication([])


def test_menu_has_expected_actions(tmp_path):
    tray = Tray(output_dir=tmp_path)
    texts = [a.text().lower() for a in tray.menu_actions()]
    assert any("pasta" in t for t in texts)
    assert any("sair" in t for t in texts)


def test_quit_action_exposed(tmp_path):
    tray = Tray(output_dir=tmp_path)
    assert tray.quit_action.text() == "Sair"
