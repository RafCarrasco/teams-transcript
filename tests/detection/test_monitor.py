"""Testes do `CallMonitor` — emissão de sinais na borda de mudança de estado."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from tt.detection.monitor import CallMonitor  # noqa: E402

_app = QApplication.instance() or QApplication([])


def test_emits_started_then_ended():
    mon = CallMonitor(poll_interval_seconds=999)
    events: list[str] = []
    mon.call_started.connect(lambda: events.append("started"))
    mon.call_ended.connect(lambda: events.append("ended"))

    mon._update(in_call=True)
    mon._update(in_call=True)   # ainda em call -> sem novo evento
    mon._update(in_call=False)
    mon._update(in_call=False)  # ainda fora -> sem novo evento

    assert events == ["started", "ended"]


def test_no_event_when_state_unchanged():
    mon = CallMonitor()
    events: list[str] = []
    mon.call_started.connect(lambda: events.append("started"))

    mon._update(in_call=False)  # já estava fora
    assert events == []
