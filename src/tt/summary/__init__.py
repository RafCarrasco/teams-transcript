"""Geração de resumo estruturado a partir de transcrições de reunião.

Recebe uma transcrição pronta (markdown ou texto) e produz um resumo
estruturado — TL;DR, decisões, action items, pontos abertos e follow-ups —
usando um provedor de LLM.

Provedor padrão: Google Gemini (`gemini-2.5-flash`), free tier, via SDK
`google-genai`. A camada de provider é abstraída por um Protocol
(`SummaryProvider`), o que permite injetar fakes nos testes e, no futuro,
adicionar Anthropic/OpenAI.

Uso típico::

    from pathlib import Path
    from tt.summary import summarize_file

    summarize_file(Path("meetings/2026-05-21-call.md"))
"""

from __future__ import annotations

from tt.summary.extractors import MeetingSummary, parse_summary
from tt.summary.formatter import segments_to_markdown, summary_to_markdown
from tt.summary.gemini_client import GeminiProvider, SummaryProvider, get_provider
from tt.summary.pipeline import summarize_file
from tt.summary.prompts import SYSTEM_PROMPT, build_user_prompt

__all__ = [
    "MeetingSummary",
    "parse_summary",
    "segments_to_markdown",
    "summary_to_markdown",
    "GeminiProvider",
    "SummaryProvider",
    "get_provider",
    "summarize_file",
    "SYSTEM_PROMPT",
    "build_user_prompt",
]
