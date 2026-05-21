"""Subpacote de áudio: captura, buffering e enumeração de dispositivos.

Importar este pacote NÃO carrega as dependências pesadas de áudio
(`sounddevice`, `soundcard`, `soundfile`). Esses imports são preguiçosos
(feitos dentro das funções de `devices.py` e `capture.py`), então ambientes
sem essas libs — como CI rodando só os testes de lógica pura — ainda
conseguem importar `tt.audio` e usar o `RingBuffer`/`mix_to_mono`.
"""

from __future__ import annotations

from tt.audio.buffer import RingBuffer, mix_to_mono

__all__ = ["RingBuffer", "mix_to_mono"]
