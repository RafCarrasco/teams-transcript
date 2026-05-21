"""Separação dos canais do WAV estéreo e merge dos segments dos 2 canais.

A captura grava WAV estéreo: canal esquerdo = microfone (você), canal direito
= loopback do sistema (os outros). Cada canal é transcrito separadamente;
depois os segments são rotulados e fundidos por tempo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

SPEAKER_SELF = "Você"
SPEAKER_OTHERS = "Outros"


def split_stereo_wav(wav_path: str | Path) -> tuple[np.ndarray, np.ndarray, int]:
    """Lê um WAV e devolve ``(mic, loopback, sample_rate)``.

    `mic` é o canal L, `loopback` é o canal R, ambos float32 mono. Se o WAV
    for mono, ambos recebem o mesmo sinal.
    """
    import soundfile as sf

    data, sample_rate = sf.read(str(wav_path), dtype="float32", always_2d=True)
    if data.shape[1] >= 2:
        return data[:, 0], data[:, 1], sample_rate
    return data[:, 0], data[:, 0], sample_rate


def label_and_merge(
    mic_segments: list[dict], loopback_segments: list[dict]
) -> list[dict]:
    """Rotula e funde os segments dos dois canais, ordenados por ``start``.

    Não muta os dicts de entrada — devolve cópias rasas novas.

    Args:
        mic_segments: segments do canal do microfone -> speaker "Você".
        loopback_segments: segments do canal do sistema -> speaker "Outros".
    """
    merged: list[dict] = []
    for seg in mic_segments:
        merged.append({**seg, "speaker": SPEAKER_SELF})
    for seg in loopback_segments:
        merged.append({**seg, "speaker": SPEAKER_OTHERS})
    merged.sort(key=lambda s: s["start"])
    return merged
