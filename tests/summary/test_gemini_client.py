"""Testes do cliente Gemini e da factory de providers."""

from __future__ import annotations

import pytest

from tt.summary.gemini_client import GeminiProvider, SummaryProvider, get_provider


def test_gemini_provider_satisfaz_o_protocol() -> None:
    provider = GeminiProvider(api_key="fake-key", model="gemini-2.5-flash")

    assert isinstance(provider, SummaryProvider)


def test_gemini_provider_cria_client_com_api_key(mocker) -> None:
    client_cls = mocker.patch("tt.summary.gemini_client.genai.Client")

    GeminiProvider(api_key="minha-chave", model="gemini-2.5-flash")

    client_cls.assert_called_once_with(api_key="minha-chave")


def test_gemini_provider_generate_chama_o_sdk_corretamente(mocker) -> None:
    client_cls = mocker.patch("tt.summary.gemini_client.genai.Client")
    fake_client = client_cls.return_value
    fake_client.models.generate_content.return_value.text = "## TL;DR\n- ok"

    provider = GeminiProvider(api_key="k", model="gemini-2.5-flash")
    result = provider.generate(system="instrução do sistema", user="prompt do usuário")

    assert result == "## TL;DR\n- ok"
    fake_client.models.generate_content.assert_called_once()
    kwargs = fake_client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-2.5-flash"
    assert kwargs["contents"] == "prompt do usuário"
    # o system prompt vai no config.system_instruction
    assert kwargs["config"].system_instruction == "instrução do sistema"


def test_gemini_provider_generate_erra_se_resposta_sem_texto(mocker) -> None:
    client_cls = mocker.patch("tt.summary.gemini_client.genai.Client")
    fake_client = client_cls.return_value
    fake_client.models.generate_content.return_value.text = None

    provider = GeminiProvider(api_key="k", model="gemini-2.5-flash")

    with pytest.raises(RuntimeError, match="vazia"):
        provider.generate(system="s", user="u")


def test_get_provider_google_retorna_gemini_provider(mocker) -> None:
    mocker.patch("tt.summary.gemini_client.genai.Client")

    provider = get_provider("google", model="gemini-2.5-flash", api_key="k")

    assert isinstance(provider, GeminiProvider)


def test_get_provider_erra_para_provider_nao_implementado() -> None:
    with pytest.raises(NotImplementedError, match="anthropic"):
        get_provider("anthropic", model="claude", api_key="k")

    with pytest.raises(NotImplementedError, match="openai"):
        get_provider("openai", model="gpt", api_key="k")


def test_get_provider_erra_para_provider_desconhecido() -> None:
    with pytest.raises(ValueError, match="desconhecido"):
        get_provider("inexistente", model="x", api_key="k")
