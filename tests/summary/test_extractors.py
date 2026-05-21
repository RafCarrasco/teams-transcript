"""Testes do parser de output estruturado do LLM."""

from __future__ import annotations

from tt.summary.extractors import MeetingSummary, parse_summary

SAMPLE = """## TL;DR
- Revisão do quote do vendor
- Definição de prazo de entrega
- Alinhamento sobre orçamento

## Decisões
- Aprovar o quote do vendor A
- Adiar a compra do item secundário

## Action items
- Ana: enviar o contrato revisado (sexta-feira)
- Bruno: agendar call com o vendor

## Pontos abertos
- Falta validar o orçamento de 2027

## Follow-ups
- Marcar reunião de follow-up na próxima semana
"""


def test_parse_summary_extrai_tldr() -> None:
    summary = parse_summary(SAMPLE)

    assert summary.tldr == [
        "Revisão do quote do vendor",
        "Definição de prazo de entrega",
        "Alinhamento sobre orçamento",
    ]


def test_parse_summary_extrai_decisoes() -> None:
    summary = parse_summary(SAMPLE)

    assert summary.decisions == [
        "Aprovar o quote do vendor A",
        "Adiar a compra do item secundário",
    ]


def test_parse_summary_extrai_action_items() -> None:
    summary = parse_summary(SAMPLE)

    assert summary.action_items == [
        "Ana: enviar o contrato revisado (sexta-feira)",
        "Bruno: agendar call com o vendor",
    ]


def test_parse_summary_extrai_pontos_abertos_e_follow_ups() -> None:
    summary = parse_summary(SAMPLE)

    assert summary.open_points == ["Falta validar o orçamento de 2027"]
    assert summary.follow_ups == ["Marcar reunião de follow-up na próxima semana"]


def test_parse_summary_retorna_meeting_summary() -> None:
    assert isinstance(parse_summary(SAMPLE), MeetingSummary)


def test_parse_summary_tolera_secao_vazia() -> None:
    markdown = """## TL;DR
- Único ponto

## Decisões

## Action items
- Carlos: revisar doc

## Pontos abertos

## Follow-ups
"""
    summary = parse_summary(markdown)

    assert summary.tldr == ["Único ponto"]
    assert summary.decisions == []
    assert summary.action_items == ["Carlos: revisar doc"]
    assert summary.open_points == []
    assert summary.follow_ups == []


def test_parse_summary_tolera_variacoes_de_heading() -> None:
    # headings com nível diferente, numeração e bullets com '*'
    markdown = """# Tl;dr
* ponto A

### 2. Decisoes
* decisão X

Action Items:
* Dani: fazer Y

## Pontos Abertos
* questão Z

## Follow ups
* contato W
"""
    summary = parse_summary(markdown)

    assert summary.tldr == ["ponto A"]
    assert summary.decisions == ["decisão X"]
    assert summary.action_items == ["Dani: fazer Y"]
    assert summary.open_points == ["questão Z"]
    assert summary.follow_ups == ["contato W"]


def test_parse_summary_ignora_marcador_nenhuma() -> None:
    markdown = """## TL;DR
- algo

## Decisões
Nenhuma

## Action items
- Eva: tarefa

## Pontos abertos
- ponto

## Follow-ups
- follow
"""
    summary = parse_summary(markdown)

    assert summary.decisions == []
