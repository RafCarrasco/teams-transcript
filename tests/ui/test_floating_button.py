"""Testes do botão flutuante.

GUI roda em modo offscreen. Aparência e always-on-top são verificação manual;
aqui se testa só a lógica de rótulo e a emissão de sinais.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from tt.ui.floating_button import FloatingButton  # noqa: E402

_app = QApplication.instance() or QApplication([])


def test_label_changes_with_state():
    btn = FloatingButton()
    btn.set_state("idle")
    assert "REC" in btn.label()
    btn.set_state("recording", elapsed="02:31")
    assert "STOP" in btn.label() and "02:31" in btn.label()
    btn.set_state("transcribing")
    assert "Transcrevendo" in btn.label()


def test_click_emits_rec_when_idle():
    btn = FloatingButton()
    btn.set_state("idle")
    fired: list[str] = []
    btn.rec_clicked.connect(lambda: fired.append("rec"))
    btn.stop_clicked.connect(lambda: fired.append("stop"))
    btn._on_click()
    assert fired == ["rec"]


def test_click_emits_stop_when_recording():
    btn = FloatingButton()
    btn.set_state("recording", elapsed="00:10")
    fired: list[str] = []
    btn.rec_clicked.connect(lambda: fired.append("rec"))
    btn.stop_clicked.connect(lambda: fired.append("stop"))
    btn._on_click()
    assert fired == ["stop"]


def test_click_ignored_when_transcribing():
    btn = FloatingButton()
    btn.set_state("transcribing")
    fired: list[str] = []
    btn.rec_clicked.connect(lambda: fired.append("rec"))
    btn.stop_clicked.connect(lambda: fired.append("stop"))
    btn._on_click()
    assert fired == []
