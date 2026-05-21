"""Smoke test: todos os módulos de `transcribe` importam sem as libs de ML.

`faster-whisper`, `pyannote.audio` e `silero-vad` NÃO estão instalados no
ambiente de CI/dev de lógica pura. Como todo import dessas libs é preguiçoso
(feito dentro de funções), importar os módulos do pacote — e até instanciar as
classes wrapper — deve funcionar mesmo assim. A falha por dependência ausente
só pode acontecer quando se *executa* a transcrição/diarização de fato.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "tt.transcribe",
        "tt.transcribe.aligner",
        "tt.transcribe.whisper_engine",
        "tt.transcribe.vad",
        "tt.transcribe.diarize",
        "tt.transcribe.pipeline",
    ],
)
def test_module_imports_without_ml_libs(module_name):
    """Cada módulo do pacote importa sem faster-whisper/pyannote/silero."""
    module = importlib.import_module(module_name)
    assert module is not None


def test_diarization_libs_absent():
    """pyannote/silero (extra `diarize`, pós-MVP) não estão no ambiente do MVP.

    `faster-whisper` (extra `transcribe`) FAZ parte do MVP e pode estar
    instalada; a diarização foi adiada para pós-MVP e fica numa extra à parte.
    """
    for lib in ("pyannote.audio", "silero_vad"):
        with pytest.raises(ImportError):
            importlib.import_module(lib)


def test_whisper_engine_instantiates_without_lib():
    """`WhisperEngine()` pode ser construído sem faster-whisper (lazy load)."""
    from tt.transcribe.whisper_engine import WhisperEngine

    engine = WhisperEngine(model="small", language="pt")
    assert engine.model_name == "small"
    assert engine.language == "pt"
    # O modelo só carrega na primeira transcrição — ainda não tocado.
    assert engine._model is None


def test_whisper_transcribe_raises_clear_error_without_lib():
    """Sem faster-whisper, transcrever levanta ImportError acionável.

    Só roda quando a extra `transcribe` NÃO está instalada — no ambiente do
    MVP, com faster-whisper presente, este caminho de erro não se aplica.
    """
    try:
        import faster_whisper  # noqa: F401

        pytest.skip("faster-whisper instalado — caminho de erro não aplicável")
    except ImportError:
        pass

    from tt.transcribe.whisper_engine import WhisperEngine

    with pytest.raises(ImportError, match="faster-whisper"):
        WhisperEngine().transcribe("inexistente.wav")


def test_vad_instantiates_without_lib():
    """`VAD()` pode ser construído sem silero-vad (lazy load)."""
    from tt.transcribe.vad import VAD

    vad = VAD()
    assert vad._model is None


def test_diarizer_requires_hf_token():
    """`Diarizer` exige token HF não-vazio no construtor."""
    from tt.transcribe.diarize import Diarizer

    with pytest.raises(ValueError, match="token"):
        Diarizer(hf_token="")


def test_diarizer_instantiates_with_token_without_lib():
    """`Diarizer` com token pode ser construído sem pyannote (lazy load)."""
    from tt.transcribe.diarize import Diarizer

    diarizer = Diarizer(hf_token="fake-token", max_speakers=4)
    assert diarizer.max_speakers == 4
    assert diarizer._pipeline is None
