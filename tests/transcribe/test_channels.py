"""Testes de split de WAV estéreo e merge dos segments (`tt.transcribe.channels`)."""

from __future__ import annotations

import numpy as np
import soundfile as sf

from tt.transcribe.channels import label_and_merge, split_stereo_wav


def test_label_and_merge_orders_by_start_and_labels():
    mic = [{"start": 4.0, "end": 6.0, "text": "bom dia"}]
    loop = [
        {"start": 0.0, "end": 3.0, "text": "olá"},
        {"start": 8.0, "end": 9.0, "text": "tchau"},
    ]
    merged = label_and_merge(mic, loop)
    assert [s["start"] for s in merged] == [0.0, 4.0, 8.0]
    assert merged[0]["speaker"] == "Outros"
    assert merged[1]["speaker"] == "Você"
    assert merged[2]["speaker"] == "Outros"


def test_label_and_merge_does_not_mutate_input():
    mic = [{"start": 1.0, "end": 2.0, "text": "x"}]
    label_and_merge(mic, [])
    assert "speaker" not in mic[0]


def test_label_and_merge_empty():
    assert label_and_merge([], []) == []


def test_split_stereo_wav(tmp_path):
    sr = 16000
    mic = np.full(sr, 0.1, dtype=np.float32)
    loop = np.full(sr, 0.2, dtype=np.float32)
    stereo = np.stack([mic, loop], axis=1)  # (N, 2): L=mic, R=loopback
    wav = tmp_path / "s.wav"
    sf.write(wav, stereo, sr)

    got_mic, got_loop, got_sr = split_stereo_wav(wav)

    assert got_sr == sr
    assert np.allclose(got_mic, 0.1, atol=1e-3)
    assert np.allclose(got_loop, 0.2, atol=1e-3)


def test_split_mono_wav_duplicates_channel(tmp_path):
    sr = 16000
    mono = np.full(sr, 0.3, dtype=np.float32)
    wav = tmp_path / "m.wav"
    sf.write(wav, mono, sr)

    got_mic, got_loop, got_sr = split_stereo_wav(wav)

    assert np.allclose(got_mic, got_loop)
