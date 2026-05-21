"""Renderização de segments de transcrição para arquivo .txt.

Formato (UTF-8):

    Transcrição — 2026-05-21 14:30
    ────────────────────────────────
    [00:00:04] Você: bom dia pessoal
    [00:00:08] Outros: vamos revisar o quote
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

_RULE = "─" * 32


def format_timestamp(seconds: float) -> str:
    """Segundos -> ``HH:MM:SS`` (fração truncada)."""
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def segments_to_txt(segments: list[dict], started_at: datetime) -> str:
    """Renderiza os segments como o conteúdo completo do .txt.

    Args:
        segments: dicts ``{start, end, speaker, text}``, ordenados por start.
            ``speaker`` ausente é renderizado como "Outros".
        started_at: hora de início da gravação (vai no cabeçalho).
    """
    lines = [f"Transcrição — {started_at:%Y-%m-%d %H:%M}", _RULE]
    for seg in segments:
        ts = format_timestamp(seg["start"])
        speaker = seg.get("speaker", "Outros")
        text = seg["text"].strip()
        lines.append(f"[{ts}] {speaker}: {text}")
    return "\n".join(lines) + "\n"


def write_txt(segments: list[dict], path: str | Path, started_at: datetime) -> Path:
    """Escreve o .txt em disco (UTF-8). Cria o diretório pai se preciso."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(segments_to_txt(segments, started_at), encoding="utf-8")
    return path


def default_txt_path(output_dir: str | Path, started_at: datetime) -> Path:
    """Caminho padrão: ``<output_dir>/transcricao_AAAA-MM-DD_HHMM.txt``."""
    name = f"transcricao_{started_at:%Y-%m-%d_%H%M}.txt"
    return Path(output_dir).expanduser() / name
