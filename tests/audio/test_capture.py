"""Testes do ciclo de vida do `Recorder`.

A captura real depende de hardware de áudio — não testável aqui. Os métodos
`_open_streams`/`_close_streams` são substituídos por no-ops; o que se verifica
é a máquina de start/stop e o `elapsed`.
"""

from __future__ import annotations

from tt.audio.capture import Recorder


def test_recorder_starts_not_recording(tmp_path):
    rec = Recorder(tmp_path / "out.wav", sample_rate=16000)
    assert rec.is_recording is False
    assert rec.elapsed == 0.0


def test_recorder_lifecycle(tmp_path, monkeypatch):
    rec = Recorder(tmp_path / "out.wav", sample_rate=16000)
    monkeypatch.setattr(rec, "_open_streams", lambda: None)
    monkeypatch.setattr(rec, "_close_streams", lambda: None)

    rec.start()
    assert rec.is_recording is True
    assert rec.elapsed >= 0.0

    rec.stop()
    assert rec.is_recording is False


def test_recorder_start_is_idempotent(tmp_path, monkeypatch):
    rec = Recorder(tmp_path / "out.wav")
    opens = []
    monkeypatch.setattr(rec, "_open_streams", lambda: opens.append(1))
    monkeypatch.setattr(rec, "_close_streams", lambda: None)

    rec.start()
    rec.start()  # segunda chamada não reabre streams
    assert opens == [1]


def test_recorder_stop_without_start_is_noop(tmp_path, monkeypatch):
    rec = Recorder(tmp_path / "out.wav")
    closes = []
    monkeypatch.setattr(rec, "_close_streams", lambda: closes.append(1))

    rec.stop()  # nunca iniciou
    assert closes == []
