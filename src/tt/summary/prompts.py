"""System prompt e builder do user prompt para o resumo de reuniões."""

from __future__ import annotations

SYSTEM_PROMPT = """Você é assistente que extrai insights de transcrições
de reuniões corporativas em português/inglês. Você produz outputs estruturados
e factuais, sem inferir o que não foi dito explicitamente.

Regras:
- Action items só se foram explicitamente atribuídos a alguém
- Decisões só se houve consenso ou definição clara
- Use o nome real dos speakers quando identificado
- Markdown structured output"""


_USER_PROMPT_TEMPLATE = """Analise a transcrição de reunião abaixo e produza um \
resumo em markdown com exatamente estas cinco seções, cada uma com um heading \
de nível 2 (`##`):

## TL;DR
Três bullets resumindo a reunião.

## Decisões
Lista de decisões tomadas. Só inclua se houve consenso ou definição clara.
Escreva "Nenhuma" se não houve decisões.

## Action items
Lista de tarefas, uma por linha, no formato `[responsável]: [tarefa] (deadline)`.
O deadline é opcional — omita os parênteses se não foi mencionado.
Só inclua itens explicitamente atribuídos a alguém.

## Pontos abertos
Questões levantadas mas não resolvidas durante a reunião.

## Follow-ups
Próximos passos, reuniões ou contatos a serem feitos depois.

Responda apenas com o markdown das cinco seções, sem texto extra.

---
TRANSCRIÇÃO:
{transcript}
"""


def build_user_prompt(transcript: str) -> str:
    """Monta o user prompt pedindo as 5 seções e injeta a transcrição.

    Args:
        transcript: texto da transcrição (markdown ou texto puro).

    Returns:
        O prompt completo a ser enviado ao LLM.
    """
    return _USER_PROMPT_TEMPLATE.format(transcript=transcript)
