"""Orquestração do pipeline de resumo.

`summarize_file` lê uma transcrição em markdown, pede o resumo ao provedor
de LLM, faz parse do output estruturado e anexa a seção
`## Resumo gerado por IA` ao próprio arquivo.
"""

from __future__ import annotations

from pathlib import Path

from tt.summary.extractors import parse_summary
from tt.summary.formatter import summary_to_markdown
from tt.summary.gemini_client import SummaryProvider, get_provider
from tt.summary.prompts import SYSTEM_PROMPT, build_user_prompt

# --- Config stub --------------------------------------------------------------
# A configuração real (provider, model, api_key) virá de `tt.utils.config`,
# lendo `settings.yaml` (ver chave `summary:`). Enquanto esse módulo não existe,
# usamos estes defaults. NÃO há API key no ambiente — em produção a chave vem
# de ${GEMINI_API_KEY}. Para testes, sempre injete `provider`.
_DEFAULT_PROVIDER = "google"
_DEFAULT_MODEL = "gemini-2.5-flash"


def _build_default_provider() -> SummaryProvider:
    """Constrói o provider padrão a partir da config (stub).

    TODO: substituir pela leitura real de `tt.utils.config` quando existir.
    """
    import os

    api_key = os.environ.get("GEMINI_API_KEY", "")
    return get_provider(_DEFAULT_PROVIDER, model=_DEFAULT_MODEL, api_key=api_key)


def summarize_file(transcript_path: Path, provider: SummaryProvider | None = None) -> None:
    """Gera o resumo de uma transcrição e o anexa ao arquivo.

    Lê o markdown em `transcript_path`, chama o LLM, faz parse do resultado
    e acrescenta a seção `## Resumo gerado por IA` ao final do arquivo —
    o conteúdo original é preservado.

    Args:
        transcript_path: caminho do arquivo de transcrição em markdown.
        provider: `SummaryProvider` a usar. Se `None`, constrói o
            `GeminiProvider` a partir da config (stub — ver `_build_default_provider`).

    Raises:
        FileNotFoundError: se `transcript_path` não existir.
    """
    path = Path(transcript_path)
    if not path.is_file():
        raise FileNotFoundError(f"Transcrição não encontrada: {path}")

    transcript = path.read_text(encoding="utf-8")

    if provider is None:
        provider = _build_default_provider()

    raw = provider.generate(system=SYSTEM_PROMPT, user=build_user_prompt(transcript))
    summary = parse_summary(raw)
    section = summary_to_markdown(summary)

    existing = transcript if transcript.endswith("\n") else transcript + "\n"
    path.write_text(f"{existing}\n{section}\n", encoding="utf-8")
