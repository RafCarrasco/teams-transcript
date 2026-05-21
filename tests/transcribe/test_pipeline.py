"""Testes do pipeline de transcrição.

A renderização markdown e a orquestração são testáveis sem libs de ML: os
engines pesados (Whisper, diarização, VAD) são substituídos por fakes via
monkeypatch. O que não dá para testar aqui é a inferência real dos modelos.
"""

from __future__ import annotations

from tt.transcribe import pipeline as pl
from tt.transcribe.pipeline import (
    _fallback_markdown,
    _format_timestamp,
    transcribe_file,
)

# --------------------------------------------------------------------------
# Helpers de formatação — lógica pura
# --------------------------------------------------------------------------


def test_format_timestamp():
    """Segundos viram [HH:MM:SS] com zero-padding."""
    assert _format_timestamp(0) == "[00:00:00]"
    assert _format_timestamp(65) == "[00:01:05]"
    assert _format_timestamp(3661) == "[01:01:01]"


def test_format_timestamp_clamps_negative():
    """Tempo negativo é tratado como zero (defensivo)."""
    assert _format_timestamp(-5) == "[00:00:00]"


def test_fallback_markdown_with_speakers():
    """Com speaker, cada linha leva o rótulo em negrito."""
    segments = [
        {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00", "text": "Bom dia."},
        {"start": 3.0, "end": 6.0, "speaker": "SPEAKER_01", "text": "Ola."},
    ]

    md = _fallback_markdown(segments)

    assert md.startswith("# Transcrição")
    assert "[00:00:00] **SPEAKER_00:** Bom dia." in md
    assert "[00:00:03] **SPEAKER_01:** Ola." in md


def test_fallback_markdown_without_speakers():
    """Sem speaker, a linha sai só com timestamp e texto."""
    segments = [{"start": 0.0, "end": 3.0, "text": "Sem diarizacao."}]

    md = _fallback_markdown(segments)

    assert "[00:00:00] Sem diarizacao." in md
    assert "**" not in md


def test_fallback_markdown_empty():
    """Lista vazia ainda produz um documento com título."""
    md = _fallback_markdown([])

    assert md.strip() == "# Transcrição"


# --------------------------------------------------------------------------
# transcribe_file — orquestração, com engines fake
# --------------------------------------------------------------------------


class _FakeWhisper:
    """WhisperEngine fake — devolve segments fixos sem tocar em modelo."""

    def __init__(self, *args, **kwargs):
        pass

    def transcribe(self, wav_path):
        return [
            {"start": 0.0, "end": 3.0, "text": "Bom dia pessoal."},
            {"start": 3.0, "end": 6.0, "text": "Vamos comecar."},
        ]


class _FakeDiarizer:
    """Diarizer fake — devolve turnos fixos sem tocar em pyannote."""

    def __init__(self, *args, **kwargs):
        pass

    def diarize(self, wav_path):
        return [
            {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"},
            {"start": 3.0, "end": 6.0, "speaker": "SPEAKER_01"},
        ]


def test_transcribe_file_writes_markdown_with_diarization(tmp_path, monkeypatch):
    """Fluxo completo com diarização: speakers aparecem no markdown."""
    # Substitui os imports preguiçosos que o pipeline faz.
    monkeypatch.setattr("tt.transcribe.whisper_engine.WhisperEngine", _FakeWhisper)
    monkeypatch.setattr("tt.transcribe.diarize.Diarizer", _FakeDiarizer)

    wav = tmp_path / "call.wav"
    wav.write_bytes(b"fake")
    out = tmp_path / "out.md"

    transcribe_file(wav, out, diarize=True, hf_token="fake-token", vad=False)

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "SPEAKER_00" in content
    assert "SPEAKER_01" in content
    assert "Bom dia pessoal." in content


def test_transcribe_file_without_diarization(tmp_path, monkeypatch):
    """Sem diarização: segments fundidos num bloco só, sem speaker."""
    monkeypatch.setattr("tt.transcribe.whisper_engine.WhisperEngine", _FakeWhisper)

    wav = tmp_path / "call.wav"
    wav.write_bytes(b"fake")
    out = tmp_path / "out.md"

    transcribe_file(wav, out, diarize=False, vad=False)

    content = out.read_text(encoding="utf-8")
    assert "SPEAKER" not in content
    # merge_consecutive funde os dois segments sem speaker num bloco só.
    assert "Bom dia pessoal. Vamos comecar." in content


def test_transcribe_file_diarize_true_without_token_skips_diarization(
    tmp_path, monkeypatch
):
    """diarize=True sem token HF: diarização pulada, transcrição segue."""
    monkeypatch.setattr("tt.transcribe.whisper_engine.WhisperEngine", _FakeWhisper)

    wav = tmp_path / "call.wav"
    wav.write_bytes(b"fake")
    out = tmp_path / "out.md"

    # Sem hf_token — não deve quebrar nem tocar no Diarizer.
    transcribe_file(wav, out, diarize=True, vad=False)

    content = out.read_text(encoding="utf-8")
    assert "SPEAKER" not in content
    assert "Bom dia pessoal." in content


def test_transcribe_file_creates_output_parent_dir(tmp_path, monkeypatch):
    """O diretório de saída é criado se não existir."""
    monkeypatch.setattr("tt.transcribe.whisper_engine.WhisperEngine", _FakeWhisper)

    wav = tmp_path / "call.wav"
    wav.write_bytes(b"fake")
    out = tmp_path / "nested" / "deep" / "out.md"

    transcribe_file(wav, out, diarize=False, vad=False)

    assert out.exists()


def test_render_markdown_prefers_summary_formatter(monkeypatch):
    """Se tt.summary.formatter.segments_to_markdown existir, ele é usado."""
    import sys
    import types

    fake_formatter = types.ModuleType("tt.summary.formatter")
    fake_formatter.segments_to_markdown = lambda segs: "FORMATTER USADO"
    monkeypatch.setitem(sys.modules, "tt.summary.formatter", fake_formatter)

    result = pl._render_markdown([{"start": 0.0, "end": 1.0, "text": "x"}])

    assert result == "FORMATTER USADO"
