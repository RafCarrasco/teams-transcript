"""Parse do output estruturado em markdown produzido pelo LLM.

O LLM responde com cinco seções em headings markdown. Este módulo converte
esse texto numa dataclass `MeetingSummary`, sendo tolerante a variações
comuns de formatação (nível do heading, numeração, `-`/`*` nos bullets,
acentuação e maiúsculas/minúsculas).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class MeetingSummary:
    """Resumo estruturado de uma reunião."""

    tldr: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    open_points: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)


# Marcadores que o LLM pode usar para indicar "seção vazia".
_EMPTY_MARKERS = {"nenhuma", "nenhum", "n/a", "na", "none", "-", "sem itens"}

# Palavras-chave -> campo da dataclass. A detecção da seção normaliza o
# heading (sem acento, minúsculo, sem pontuação) e procura essas chaves.
_SECTION_KEYS: list[tuple[tuple[str, ...], str]] = [
    (("tldr", "tl dr", "resumo"), "tldr"),
    (("decisoes", "decisao", "decisions", "decision"), "decisions"),
    (("action items", "action item", "acoes", "tarefas"), "action_items"),
    (("pontos abertos", "ponto aberto", "open points", "questoes"), "open_points"),
    (("follow ups", "follow up", "followups", "proximos passos"), "follow_ups"),
]


def _normalize(text: str) -> str:
    """Minúsculas, sem acentos, sem pontuação — para comparar headings."""
    no_accent = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", no_accent.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _match_section(heading: str) -> str | None:
    """Retorna o nome do campo se o heading corresponder a uma seção."""
    norm = _normalize(heading)
    # remove numeração inicial ("2 decisoes" -> "decisoes")
    norm = re.sub(r"^\d+\s*", "", norm)
    for keys, attr in _SECTION_KEYS:
        if any(key in norm for key in keys):
            return attr
    return None


def _is_heading(line: str) -> tuple[bool, str]:
    """Detecta headings markdown (`#`) ou `Texto:` como cabeçalho de seção."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return True, stripped.lstrip("#").strip()
    # heading "solto" terminando em ':' — ex.: "Action Items:"
    if stripped.endswith(":") and len(stripped) <= 40 and not stripped.startswith(("-", "*")):
        return True, stripped.rstrip(":").strip()
    return False, ""


def _clean_bullet(line: str) -> str:
    """Remove o marcador de bullet (`-`, `*`, `1.`) e espaços."""
    stripped = line.strip()
    stripped = re.sub(r"^([-*•]|\d+[.)])\s*", "", stripped)
    return stripped.strip()


def parse_summary(markdown: str) -> MeetingSummary:
    """Faz parse do markdown estruturado retornado pelo LLM.

    Args:
        markdown: texto em markdown com as cinco seções.

    Returns:
        `MeetingSummary` com as listas extraídas. Seções ausentes ou vazias
        viram listas vazias.
    """
    sections: dict[str, list[str]] = {
        "tldr": [],
        "decisions": [],
        "action_items": [],
        "open_points": [],
        "follow_ups": [],
    }
    current: str | None = None

    for line in markdown.splitlines():
        is_head, heading_text = _is_heading(line)
        if is_head:
            matched = _match_section(heading_text) if heading_text else None
            # heading reconhecido troca a seção; heading desconhecido encerra.
            current = matched
            continue

        if current is None:
            continue

        if not line.strip():
            continue

        item = _clean_bullet(line)
        if not item:
            continue
        if _normalize(item) in _EMPTY_MARKERS:
            continue
        sections[current].append(item)

    return MeetingSummary(
        tldr=sections["tldr"],
        decisions=sections["decisions"],
        action_items=sections["action_items"],
        open_points=sections["open_points"],
        follow_ups=sections["follow_ups"],
    )
