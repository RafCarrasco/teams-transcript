"""Testes do builder de prompts."""

from __future__ import annotations

from tt.summary.prompts import SYSTEM_PROMPT, build_user_prompt


def test_build_user_prompt_inclui_a_transcricao() -> None:
    transcript = "[00:00:00] SPEAKER_00: Bom dia, vamos comecar a reuniao."

    prompt = build_user_prompt(transcript)

    assert transcript in prompt


def test_build_user_prompt_pede_as_cinco_secoes() -> None:
    prompt = build_user_prompt("transcricao qualquer").lower()

    assert "tl;dr" in prompt
    assert "decis" in prompt          # decisoes / decisões
    assert "action item" in prompt
    assert "pontos abertos" in prompt
    assert "follow-up" in prompt


def test_build_user_prompt_descreve_formato_do_action_item() -> None:
    prompt = build_user_prompt("x")

    assert "[responsável]" in prompt
    assert "[tarefa]" in prompt
    assert "(deadline)" in prompt


def test_system_prompt_tem_regras_factuais() -> None:
    assert "Action items" in SYSTEM_PROMPT
    assert "explicitamente" in SYSTEM_PROMPT
