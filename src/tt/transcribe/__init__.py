"""Subpacote de transcrição: Whisper + VAD + diarização + alinhamento.

Importar este pacote NÃO carrega as dependências pesadas de ML
(`faster-whisper`, `pyannote.audio`, `silero-vad`). Todos os imports dessas
libs são preguiçosos — feitos dentro das funções/métodos que de fato as usam.
Assim, ambientes sem essas libs (CI de lógica pura, dev sem GPU) ainda
conseguem `import tt.transcribe` e exercitar a lógica pura do `aligner`.

Peças:
    WhisperEngine   transcreve um WAV em segments de texto
    VAD             corta silêncio antes do Whisper (Silero)
    Diarizer        identifica "quem falou quando" (pyannote)
    align           cola um speaker em cada segment de texto (lógica pura)
    merge_consecutive  funde segments adjacentes do mesmo speaker (lógica pura)
    transcribe_file orquestra tudo: WAV -> markdown

Formato de segment usado em todo o pacote:
    {"start": float, "end": float, "text": str, ["speaker": str]}
Tempos em segundos.
"""

from __future__ import annotations

from tt.transcribe.aligner import align, merge_consecutive
from tt.transcribe.pipeline import transcribe_file

__all__ = [
    "align",
    "merge_consecutive",
    "transcribe_file",
]
