"""Fixtures compartilhadas entre os testes."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_segments() -> list[dict]:
    """Segments de transcrição fake — formato comum do pipeline.

    Cada segment: start/end em segundos, texto, e speaker opcional.
    """
    return [
        {"start": 0.0, "end": 3.2, "speaker": "SPEAKER_00", "text": "Bom dia pessoal."},
        {"start": 3.5, "end": 8.1, "speaker": "SPEAKER_01", "text": "Vamos revisar o quote."},
        {"start": 8.4, "end": 12.0, "speaker": "SPEAKER_00", "text": "Fechado, mando sexta."},
    ]
