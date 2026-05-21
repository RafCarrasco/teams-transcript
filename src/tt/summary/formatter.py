"""Renderização markdown — transcrição e resumo gerado por IA."""

from __future__ import annotations

from tt.summary.extractors import MeetingSummary


def _format_timestamp(seconds: float) -> str:
    """Converte segundos em `HH:MM:SS`."""
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def segments_to_markdown(segments: list[dict]) -> str:
    """Renderiza segments de transcrição em markdown.

    Cada segment é um dict com `start`, `end`, `text` e, opcionalmente,
    `speaker`. A saída tem uma linha por segment no formato
    `[HH:MM:SS] **Speaker:** texto`.

    Args:
        segments: lista de segments da transcrição.

    Returns:
        Markdown com uma linha por segment.
    """
    lines: list[str] = []
    for seg in segments:
        ts = _format_timestamp(float(seg.get("start", 0.0)))
        speaker = seg.get("speaker")
        text = str(seg.get("text", "")).strip()
        if speaker:
            lines.append(f"[{ts}] **{speaker}:** {text}")
        else:
            lines.append(f"[{ts}] {text}")
    return "\n".join(lines)


def _render_list(items: list[str], empty_label: str) -> str:
    """Renderiza uma lista em bullets, ou um marcador se vazia."""
    if not items:
        return f"_{empty_label}_"
    return "\n".join(f"- {item}" for item in items)


def summary_to_markdown(summary: MeetingSummary) -> str:
    """Renderiza a seção `## Resumo gerado por IA` a partir do resumo.

    Args:
        summary: o `MeetingSummary` estruturado.

    Returns:
        Bloco markdown pronto para anexar a um arquivo de transcrição.
    """
    parts = [
        "## Resumo gerado por IA",
        "",
        "### TL;DR",
        _render_list(summary.tldr, "Nenhum"),
        "",
        "### Decisões",
        _render_list(summary.decisions, "Nenhuma"),
        "",
        "### Action items",
        _render_list(summary.action_items, "Nenhum"),
        "",
        "### Pontos abertos",
        _render_list(summary.open_points, "Nenhum"),
        "",
        "### Follow-ups",
        _render_list(summary.follow_ups, "Nenhum"),
    ]
    return "\n".join(parts)
