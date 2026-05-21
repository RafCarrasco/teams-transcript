"""Cliente Gemini e abstração de provider de LLM.

O resumo é gerado por um provedor de LLM atrás de um `Protocol`
(`SummaryProvider`). Isso desacopla o pipeline do SDK concreto: nos testes
injetamos um fake; em produção usamos `GeminiProvider`.

Provider padrão: Google Gemini via SDK `google-genai`. A API usada::

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=...)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    text = response.text
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from google import genai
from google.genai import types


@runtime_checkable
class SummaryProvider(Protocol):
    """Provedor de LLM capaz de gerar um resumo a partir de prompts."""

    def generate(self, system: str, user: str) -> str:
        """Gera texto a partir de um system prompt e um user prompt."""
        ...


class GeminiProvider:
    """`SummaryProvider` baseado no Google Gemini (`google-genai`)."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        """Inicializa o cliente Gemini.

        Args:
            api_key: chave da API do Google AI Studio (free tier).
            model: nome do modelo, ex.: `gemini-2.5-flash`.
        """
        self._model = model
        self._client = genai.Client(api_key=api_key)

    def generate(self, system: str, user: str) -> str:
        """Chama o Gemini e devolve o texto da resposta.

        Args:
            system: instrução de sistema (vai em `config.system_instruction`).
            user: prompt do usuário (vai em `contents`).

        Returns:
            O texto gerado pelo modelo.

        Raises:
            RuntimeError: se o modelo não devolver texto.
        """
        response = self._client.models.generate_content(
            model=self._model,
            contents=user,
            config=types.GenerateContentConfig(system_instruction=system),
        )
        text = response.text
        if not text:
            raise RuntimeError("Resposta do Gemini veio vazia (sem texto).")
        return text


def get_provider(provider: str, model: str, api_key: str) -> SummaryProvider:
    """Factory de `SummaryProvider`.

    Args:
        provider: identificador do provedor (`google`, `anthropic`, `openai`).
        model: nome do modelo a usar.
        api_key: chave da API.

    Returns:
        Uma instância de `SummaryProvider`.

    Raises:
        NotImplementedError: provider conhecido mas ainda não implementado.
        ValueError: provider desconhecido.
    """
    key = provider.strip().lower()
    if key == "google":
        return GeminiProvider(api_key=api_key, model=model)
    if key in ("anthropic", "openai"):
        raise NotImplementedError(
            f"Provider '{key}' ainda não foi implementado — use 'google' (Gemini)."
        )
    raise ValueError(
        f"Provider desconhecido: '{provider}'. Opções válidas: google, anthropic, openai."
    )
