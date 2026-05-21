"""Testes da heurística de "está em call" — lógica pura (numpy)."""

from __future__ import annotations

import numpy as np
import pytest

from tt.detection.call_state import DEFAULT_RMS_THRESHOLD, is_in_call, rms

# --------------------------------------------------------------------------
# rms
# --------------------------------------------------------------------------


def test_rms_of_silence_is_zero():
    assert rms(np.zeros(1000, dtype=np.float32)) == 0.0


def test_rms_of_empty_array_is_zero():
    assert rms(np.array([], dtype=np.float32)) == 0.0


def test_rms_of_constant_signal():
    # RMS de um sinal constante == |valor|.
    samples = np.full(500, 0.5, dtype=np.float32)
    assert rms(samples) == pytest.approx(0.5, rel=1e-5)


def test_rms_of_full_scale_sine():
    # RMS de uma senoide de amplitude 1.0 == 1/sqrt(2) ~= 0.707.
    t = np.linspace(0, 1, 16000, endpoint=False, dtype=np.float32)
    sine = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    assert rms(sine) == pytest.approx(1 / np.sqrt(2), rel=1e-3)


def test_rms_is_nonnegative_for_negative_signal():
    samples = np.full(100, -0.8, dtype=np.float32)
    assert rms(samples) == pytest.approx(0.8, rel=1e-5)


def test_rms_handles_stereo_input():
    # Entrada 2-D deve ser aceita (achatada) sem erro.
    stereo = np.full((100, 2), 0.5, dtype=np.float32)
    assert rms(stereo) == pytest.approx(0.5, rel=1e-5)


def test_louder_signal_has_higher_rms():
    quiet = np.full(100, 0.1, dtype=np.float32)
    loud = np.full(100, 0.9, dtype=np.float32)
    assert rms(loud) > rms(quiet)


# --------------------------------------------------------------------------
# is_in_call
# --------------------------------------------------------------------------


def test_silence_is_not_in_call():
    assert is_in_call(np.zeros(16000, dtype=np.float32)) is False


def test_empty_loopback_is_not_in_call():
    assert is_in_call(np.array([], dtype=np.float32)) is False


def test_strong_sustained_signal_is_in_call():
    # Voz/áudio de call: senoide bem acima do limiar.
    t = np.linspace(0, 1, 16000, endpoint=False, dtype=np.float32)
    voice = (0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    assert is_in_call(voice) is True


def test_faint_noise_below_threshold_is_not_in_call():
    # Ruído de fundo bem fraco — abaixo do limiar padrão.
    rng = np.random.default_rng(42)
    faint = (rng.standard_normal(16000) * 0.0005).astype(np.float32)
    assert is_in_call(faint) is False


def test_threshold_is_respected():
    # Sinal constante de RMS conhecido (0.02).
    samples = np.full(16000, 0.02, dtype=np.float32)
    # Limiar acima do sinal -> não em call.
    assert is_in_call(samples, threshold=0.05) is False
    # Limiar abaixo do sinal -> em call.
    assert is_in_call(samples, threshold=0.01) is True


def test_signal_at_threshold_counts_as_in_call():
    # 0.5 round-trip exato em float32 -> RMS == 0.5 sem erro de precisão;
    # com threshold == 0.5 a comparação `>=` deve dar in-call.
    samples = np.full(16000, 0.5, dtype=np.float32)
    assert is_in_call(samples, threshold=0.5) is True


def test_default_threshold_constant_is_sensible():
    # O limiar padrão fica entre o silêncio digital e o pico — sanidade.
    assert 0.0 < DEFAULT_RMS_THRESHOLD < 1.0
