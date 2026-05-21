"""Testes da orquestração do pipeline de resumo."""

from __future__ import annotations

from pathlib import Path

import pytest

from tt.summary.pipeline import summarize_file

LLM_OUTPUT = """## TL;DR
- Revisão do quote
- Definição de prazo

## Decisões
- Aprovar o vendor A

## Action items
- Ana: enviar contrato (sexta)

## Pontos abertos
- Validar orçamento

## Follow-ups
- Marcar nova call
"""


class FakeProvider:
    """`SummaryProvider` fake — devolve um output fixo e registra a chamada."""

    def __init__(self, output: str) -> None:
        self.output = output
        self.calls: list[tuple[str, str]] = []

    def generate(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.output


def test_summarize_file_anexa_a_secao_de_resumo(tmp_path: Path) -> None:
    transcript = tmp_path / "reuniao.md"
    transcript.write_text(
        "# Transcrição\n\n[00:00:00] SPEAKER_00: Bom dia.\n",
        encoding="utf-8",
    )
    provider = FakeProvider(LLM_OUTPUT)

    summarize_file(transcript, provider=provider)

    content = transcript.read_text(encoding="utf-8")
    assert "## Resumo gerado por IA" in content
    # conteúdo original preservado
    assert "[00:00:00] SPEAKER_00: Bom dia." in content
    # itens parseados aparecem renderizados
    assert "Revisão do quote" in content
    assert "Ana: enviar contrato (sexta)" in content


def test_summarize_file_passa_a_transcricao_ao_provider(tmp_path: Path) -> None:
    transcript = tmp_path / "reuniao.md"
    transcript.write_text("conteúdo da transcrição aqui", encoding="utf-8")
    provider = FakeProvider(LLM_OUTPUT)

    summarize_file(transcript, provider=provider)

    assert len(provider.calls) == 1
    system, user = provider.calls[0]
    assert "conteúdo da transcrição aqui" in user
    assert "factuais" in system


def test_summarize_file_acrescenta_ao_inves_de_sobrescrever(tmp_path: Path) -> None:
    transcript = tmp_path / "reuniao.md"
    original = "linha original\n"
    transcript.write_text(original, encoding="utf-8")
    provider = FakeProvider(LLM_OUTPUT)

    summarize_file(transcript, provider=provider)

    content = transcript.read_text(encoding="utf-8")
    assert content.startswith(original)
    assert content.index("linha original") < content.index("## Resumo gerado por IA")


def test_summarize_file_erra_se_arquivo_nao_existe(tmp_path: Path) -> None:
    provider = FakeProvider(LLM_OUTPUT)

    with pytest.raises(FileNotFoundError):
        summarize_file(tmp_path / "nao_existe.md", provider=provider)
