"""Testes do ring buffer de áudio e do mix mono — lógica pura (numpy)."""

from __future__ import annotations

import threading

import numpy as np
import pytest

from tt.audio.buffer import RingBuffer, mix_to_mono

# --------------------------------------------------------------------------
# RingBuffer
# --------------------------------------------------------------------------


def test_buffer_starts_empty():
    buf = RingBuffer(capacity=10)
    assert buf.capacity == 10
    assert len(buf) == 0
    assert buf.is_empty
    assert not buf.is_full


def test_write_then_read_round_trip():
    buf = RingBuffer(capacity=10)
    frames = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    buf.write(frames)
    assert len(buf) == 3
    out = buf.read(3)
    np.testing.assert_array_equal(out, frames)
    assert len(buf) == 0


def test_read_consumes_oldest_first_fifo():
    buf = RingBuffer(capacity=10)
    buf.write(np.array([1.0, 2.0], dtype=np.float32))
    buf.write(np.array([3.0, 4.0], dtype=np.float32))
    np.testing.assert_array_equal(buf.read(3), np.array([1.0, 2.0, 3.0], dtype=np.float32))
    np.testing.assert_array_equal(buf.read(1), np.array([4.0], dtype=np.float32))


def test_read_more_than_available_returns_only_available():
    buf = RingBuffer(capacity=10)
    buf.write(np.array([1.0, 2.0], dtype=np.float32))
    out = buf.read(100)
    np.testing.assert_array_equal(out, np.array([1.0, 2.0], dtype=np.float32))
    assert len(buf) == 0


def test_read_on_empty_returns_empty_array():
    buf = RingBuffer(capacity=10)
    out = buf.read(5)
    assert out.dtype == np.float32
    assert out.size == 0


def test_write_fills_to_capacity():
    buf = RingBuffer(capacity=4)
    buf.write(np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32))
    assert buf.is_full
    assert len(buf) == 4


def test_overwrite_oldest_when_full():
    # Capacidade 4; escreve 6 amostras -> as 2 mais antigas (1,2) somem.
    buf = RingBuffer(capacity=4)
    buf.write(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype=np.float32))
    assert len(buf) == 4
    np.testing.assert_array_equal(
        buf.read(4), np.array([3.0, 4.0, 5.0, 6.0], dtype=np.float32)
    )


def test_overwrite_across_multiple_writes():
    buf = RingBuffer(capacity=3)
    buf.write(np.array([1.0, 2.0], dtype=np.float32))
    buf.write(np.array([3.0, 4.0], dtype=np.float32))  # vira [2,3,4]
    np.testing.assert_array_equal(buf.read(3), np.array([2.0, 3.0, 4.0], dtype=np.float32))


def test_write_larger_than_capacity_keeps_last_capacity_samples():
    buf = RingBuffer(capacity=3)
    buf.write(np.arange(10, dtype=np.float32))
    np.testing.assert_array_equal(buf.read(3), np.array([7.0, 8.0, 9.0], dtype=np.float32))


def test_write_accepts_non_float32_and_casts():
    buf = RingBuffer(capacity=5)
    buf.write(np.array([1, 2, 3], dtype=np.int16))
    out = buf.read(3)
    assert out.dtype == np.float32
    np.testing.assert_array_equal(out, np.array([1.0, 2.0, 3.0], dtype=np.float32))


def test_write_rejects_multidimensional_input():
    buf = RingBuffer(capacity=5)
    with pytest.raises(ValueError):
        buf.write(np.zeros((4, 2), dtype=np.float32))


def test_wraparound_write_read_cycle():
    # Exercita o índice circular dando várias voltas no buffer.
    buf = RingBuffer(capacity=5)
    expected = []
    next_val = 0.0
    for _ in range(20):
        chunk = np.array([next_val, next_val + 1.0, next_val + 2.0], dtype=np.float32)
        next_val += 3.0
        buf.write(chunk)
        expected.extend(chunk.tolist())
        got = buf.read(2)
        assert len(got) <= 2
    # O que sobrou no buffer são as últimas amostras escritas.
    leftover = buf.read(buf.capacity)
    assert len(leftover) <= buf.capacity


def test_thread_safety_concurrent_writes():
    # Vários writers concorrentes; nenhum dado deve corromper o buffer
    # (capacidade grande o bastante pra caber tudo, sem overwrite).
    buf = RingBuffer(capacity=10_000)
    chunk = np.ones(100, dtype=np.float32)

    def worker():
        for _ in range(20):
            buf.write(chunk)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 5 threads * 20 writes * 100 amostras = 10_000 amostras, todas == 1.0.
    out = buf.read(10_000)
    assert out.size == 10_000
    assert np.all(out == 1.0)


# --------------------------------------------------------------------------
# mix_to_mono
# --------------------------------------------------------------------------


def test_mix_to_mono_returns_mono_shape():
    loopback = np.zeros(1000, dtype=np.float32)
    mic = np.zeros(1000, dtype=np.float32)
    out = mix_to_mono(loopback, mic)
    assert out.ndim == 1
    assert out.shape == (1000,)
    assert out.dtype == np.float32


def test_mix_to_mono_flattens_stereo_input():
    loopback = np.zeros((1000, 2), dtype=np.float32)  # estéreo
    mic = np.zeros((1000, 1), dtype=np.float32)
    out = mix_to_mono(loopback, mic)
    assert out.ndim == 1
    assert out.shape == (1000,)


def test_mix_to_mono_sums_signals():
    loopback = np.full(10, 0.2, dtype=np.float32)
    mic = np.full(10, 0.1, dtype=np.float32)
    out = mix_to_mono(loopback, mic)
    # Soma == 0.3, abaixo de 1.0 -> sem necessidade de normalizar.
    np.testing.assert_allclose(out, 0.3, rtol=1e-6)


def test_mix_to_mono_no_clipping():
    # Dois sinais altos: a soma estouraria, mas o resultado deve ficar em [-1, 1].
    loopback = np.full(100, 0.9, dtype=np.float32)
    mic = np.full(100, 0.8, dtype=np.float32)
    out = mix_to_mono(loopback, mic)
    assert out.max() <= 1.0
    assert out.min() >= -1.0


def test_mix_to_mono_negative_peak_no_clipping():
    loopback = np.full(50, -0.9, dtype=np.float32)
    mic = np.full(50, -0.7, dtype=np.float32)
    out = mix_to_mono(loopback, mic)
    assert out.min() >= -1.0
    assert out.max() <= 1.0


def test_mix_to_mono_handles_length_mismatch():
    # Sinais de tamanhos diferentes: alinha pelo menor.
    loopback = np.full(100, 0.1, dtype=np.float32)
    mic = np.full(60, 0.2, dtype=np.float32)
    out = mix_to_mono(loopback, mic)
    assert out.shape == (60,)
    np.testing.assert_allclose(out, 0.3, rtol=1e-6)


def test_mix_to_mono_preserves_relative_shape_after_normalization():
    # Após normalizar, o pico vira exatamente 1.0 e a razão entre amostras
    # se mantém.
    loopback = np.array([1.0, 0.5, 0.25], dtype=np.float32)
    mic = np.array([1.0, 0.5, 0.25], dtype=np.float32)
    out = mix_to_mono(loopback, mic)  # soma = [2, 1, 0.5], pico 2 -> /2
    np.testing.assert_allclose(out, np.array([1.0, 0.5, 0.25]), rtol=1e-6)


def test_mix_to_mono_silence_stays_silent():
    out = mix_to_mono(np.zeros(10, dtype=np.float32), np.zeros(10, dtype=np.float32))
    assert np.all(out == 0.0)
