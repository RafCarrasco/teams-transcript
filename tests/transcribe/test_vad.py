"""Testes do fallback de gating por energia do VAD — lógica pura em numpy.

Só `energy_gate` é testável aqui: o caminho neural (`VAD.strip_silence`)
depende do silero-vad, que não está instalado.
"""

from __future__ import annotations

import numpy as np

from tt.transcribe.vad import energy_gate


def test_energy_gate_drops_silent_frames():
    """Frames de silêncio são removidos; os de fala permanecem."""
    sr = 16_000
    frame = sr * 30 // 1000  # 30 ms

    silence = np.zeros(frame, dtype=np.float32)
    speech = np.full(frame, 0.5, dtype=np.float32)  # RMS = 0.5, bem acima do limiar

    audio = np.concatenate([silence, speech, silence, speech])
    result = energy_gate(audio, sample_rate=sr, frame_ms=30, threshold=0.01)

    # Sobram exatamente os dois frames de fala.
    assert result.size == 2 * frame
    assert np.allclose(result, 0.5)


def test_energy_gate_all_silence_returns_empty():
    """Áudio inteiramente silencioso resulta em array vazio."""
    audio = np.zeros(16_000, dtype=np.float32)

    result = energy_gate(audio, sample_rate=16_000)

    assert result.size == 0
    assert result.dtype == np.float32


def test_energy_gate_all_speech_keeps_everything():
    """Áudio inteiramente com fala sobrevive (a menos da cauda parcial)."""
    sr = 16_000
    frame = sr * 30 // 1000
    audio = np.full(10 * frame, 0.3, dtype=np.float32)

    result = energy_gate(audio, sample_rate=sr, frame_ms=30, threshold=0.01)

    assert result.size == 10 * frame


def test_energy_gate_empty_input():
    """Array vazio entra, array vazio sai — sem crash."""
    result = energy_gate(np.array([], dtype=np.float32))

    assert result.size == 0


def test_energy_gate_audio_shorter_than_frame():
    """Áudio mais curto que um frame é decidido pelo RMS do sinal todo."""
    loud = np.full(100, 0.5, dtype=np.float32)
    quiet = np.full(100, 0.001, dtype=np.float32)

    assert energy_gate(loud, frame_ms=30, threshold=0.01).size == 100
    assert energy_gate(quiet, frame_ms=30, threshold=0.01).size == 0


def test_energy_gate_threshold_is_respected():
    """O limiar separa fala de ruído de baixo nível."""
    sr = 16_000
    frame = sr * 30 // 1000
    quiet = np.full(frame, 0.005, dtype=np.float32)  # RMS 0.005
    loud = np.full(frame, 0.2, dtype=np.float32)  # RMS 0.2
    audio = np.concatenate([quiet, loud])

    # Limiar 0.01: o trecho quiet cai, o loud fica.
    result = energy_gate(audio, sample_rate=sr, frame_ms=30, threshold=0.01)
    assert result.size == frame
    assert np.allclose(result, 0.2)
