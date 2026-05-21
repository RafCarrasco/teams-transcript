"""Testes da renderização markdown."""

from __future__ import annotations

from tt.summary.extractors import MeetingSummary
from tt.summary.formatter import segments_to_markdown, summary_to_markdown


def test_segments_to_markdown_formata_timestamp_e_speaker(sample_segments: list[dict]) -> None:
    md = segments_to_markdown(sample_segments)

    assert "[00:00:00]" in md
    # segundo segment comeca em 3.5s -> arredonda para 00:00:04
    assert "[00:00:04]" in md
    assert "SPEAKER_00" in md
    assert "Bom dia pessoal." in md


def test_segments_to_markdown_converte_segundos_grandes_em_hms() -> None:
    segments = [{"start": 3661.0, "end": 3665.0, "speaker": "S", "text": "oi"}]

    md = segments_to_markdown(segments)

    assert "[01:01:01]" in md


def test_segments_to_markdown_tolera_speaker_ausente() -> None:
    segments = [{"start": 0.0, "end": 1.0, "text": "sem speaker"}]

    md = segments_to_markdown(segments)

    assert "sem speaker" in md
    assert "[00:00:00]" in md


def test_summary_to_markdown_tem_o_heading_de_secao() -> None:
    summary = MeetingSummary(
        tldr=["ponto um"],
        decisions=["decisão A"],
        action_items=["Ana: tarefa (sexta)"],
        open_points=["questão aberta"],
        follow_ups=["próximo passo"],
    )

    md = summary_to_markdown(summary)

    assert "## Resumo gerado por IA" in md


def test_summary_to_markdown_renderiza_todas_as_secoes() -> None:
    summary = MeetingSummary(
        tldr=["ponto um"],
        decisions=["decisão A"],
        action_items=["Ana: tarefa (sexta)"],
        open_points=["questão aberta"],
        follow_ups=["próximo passo"],
    )

    md = summary_to_markdown(summary)

    assert "ponto um" in md
    assert "decisão A" in md
    assert "Ana: tarefa (sexta)" in md
    assert "questão aberta" in md
    assert "próximo passo" in md


def test_summary_to_markdown_mostra_marcador_para_secao_vazia() -> None:
    summary = MeetingSummary(tldr=["só isso"])

    md = summary_to_markdown(summary)

    # seções vazias não quebram a renderização e exibem um marcador
    assert "## Resumo gerado por IA" in md
    assert "_Nenhum_" in md or "_Nenhuma_" in md
