# ADR 0001 — Provider de LLM para o resumo: Gemini (free tier)

- **Status:** Aceito
- **Data:** 2026-05-21
- **Decisor:** Rafael Carrasco

## Contexto

A camada de resumo (`summary/`) é a **única** parte do teams-transcript que usa
um serviço de nuvem. Toda transcrição roda local. O plano original (brief inicial,
2026-05-20) escolhia a **Anthropic Claude API** (Sonnet 4) porque já estava no
fluxo de trabalho do Rafael.

Surgiram duas restrições novas:

1. **Custo.** A Claude API é paga por token. Mesmo sendo barata para este uso
   (~$0.03/call com Sonnet, ~$1.50/mês a 50 calls), a preferência passou a ser
   **custo zero**, sem rodar modelo local.
2. **Confusão de billing.** Havia a dúvida: "uma assinatura paga ($20/mês) não
   cobriria a API?"

## Desmistificação — assinatura ≠ API

**Assinatura paga e API são sistemas de cobrança separados.**

| | ChatGPT Plus / Claude Pro ($20/mês) | API (OpenAI / Anthropic / Google) |
|---|---|---|
| O que é | Acesso ao site/app de chat | Endpoint para programas chamarem |
| Cobrança | Assinatura fixa mensal | Pré-pago por token, cartão à parte |
| Um inclui o outro? | **Não** | **Não** |

Pagar ChatGPT Plus **não** gera crédito de API. Um app não consegue usar a
assinatura do Plus — ela só funciona dentro do site/app oficial. As únicas formas
de "usar a assinatura via código" são hacks que automatizam o navegador ou fazem
engenharia reversa do site: **violam os Termos de Uso**, quebram quando o site
muda e arriscam ban da conta. Descartados.

## Decisão

Usar **Google Gemini `gemini-2.5-flash`** via SDK `google-genai`, no **free tier**
do Google AI Studio.

Motivos:

- **$0 real.** Free tier genuíno, não trial. Sem cartão de crédito.
- **Cloud.** Não roda na máquina — não consome CPU/GPU do laptop durante o resumo.
- **Qualidade suficiente.** Flash lida bem com sumarização PT-BR / EN.
- **Setup trivial.** Chave gerada em `aistudio.google.com/apikey`.

A camada `summary/` é construída com um **campo `provider`** no `settings.yaml`
(`google` | `anthropic` | `openai`). Default `google`. Trocar de provider depois
não exige mudança de arquitetura.

## Alternativas consideradas

| Opção | Custo | Veredito |
|---|---|---|
| **Gemini 2.5 Flash (free tier)** | $0 | ✅ Escolhido |
| Groq (Llama 3.3 70B, free tier) | $0 | Alternativa viável; menos previsível |
| OpenAI gpt-4o-mini (API paga) | ~$0.002/call | Barato mas não-grátis; billing à parte |
| Anthropic Claude Haiku/Sonnet | ~$0.01–0.03/call | Plano original; mais caro |
| LLM local (Llama 70B) | $0 após setup | Rejeitado: exige GPU forte; muita engenharia |

## Consequências

- **Positivas:** custo operacional cai para ~$0/mês (só storage local).
- **Limitação:** free tier tem rate limit (req/min + cota diária). Resumo é
  1 call curta por reunião, então o limite raramente é atingido. Mitigação:
  fila com retry/backoff; se necessário, trocar `provider` para opção paga.
- **Privacidade:** o transcript (texto, sem áudio) é enviado ao Google. Política
  de uso de dados do free tier do Google AI Studio difere da API paga — **revisar
  os termos atuais** antes de uso com conteúdo sensível. Ver [`docs/ideas.md`](../ideas.md).

## Pendências

- Confirmar limites atuais do free tier (req/min, cota diária) ao implementar a Fase 5.
- Confirmar a política de retenção/treino de dados do Google AI Studio free tier.
