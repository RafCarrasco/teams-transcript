"""Testes da renderização de segments para .txt (`tt.transcribe.txt_writer`)."""

from __future__ import annotations

from datetime import datetime

from tt.transcribe.txt_writer import (
    default_txt_path,
    format_timestamp,
    segments_to_txt,
    write_txt,
)


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(65) == "00:01:05"
    assert format_timestamp(3661) == "01:01:01"


def test_format_timestamp_truncates_fraction():
    assert format_timestamp(4.9) == "00:00:04"


def test_segments_to_txt_has_header_and_lines():
    segs = [
        {"start": 4.0, "end": 6.0, "speaker": "Você", "text": "bom dia"},
        {"start": 8.0, "end": 9.0, "speaker": "Outros", "text": "vamos revisar"},
    ]
    out = segments_to_txt(segs, datetime(2026, 5, 21, 14, 30))
    assert out.startswith("Transcrição — 2026-05-21 14:30")
    assert "[00:00:04] Você: bom dia" in out
    assert "[00:00:08] Outros: vamos revisar" in out


def test_segments_to_txt_speaker_defaults_to_outros():
    out = segments_to_txt([{"start": 0.0, "end": 1.0, "text": "oi"}],
                          datetime(2026, 5, 21, 14, 30))
    assert "[00:00:00] Outros: oi" in out


def test_write_txt_creates_utf8_file(tmp_path):
    path = tmp_path / "sub" / "t.txt"
    write_txt([{"start": 0.0, "end": 1.0, "speaker": "Você", "text": "olá"}],
              path, datetime(2026, 5, 21, 14, 30))
    assert path.read_text(encoding="utf-8").count("Você: olá") == 1


def test_default_txt_path():
    p = default_txt_path("/tmp/x", datetime(2026, 5, 21, 14, 30))
    assert p.name == "transcricao_2026-05-21_1430.txt"
