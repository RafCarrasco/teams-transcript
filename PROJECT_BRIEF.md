# Teams Transcript — Project Brief

> **Documento único** com tudo que se precisa saber sobre o projeto. Detalhes técnicos completos estão nos arquivos em `docs/`. Esse aqui é o resumo executivo.

---

## O que é

Ferramenta desktop local (Windows-first) que **transcreve chamadas do Microsoft Teams sem entrar na call e sem aparecer pra ninguém**. Captura o áudio do sistema (o que você ouve) + microfone (o que você fala), transcreve com Whisper local, separa quem disse o quê, e gera resumo com action items via Claude.

**Único pra quem usa.** Outros participantes nunca veem nada — não há bot, não há aviso visual no Teams, não há integração com a Microsoft Graph API.

---

## Por que esse projeto existe

**Problemas que resolve:**

- Tomar notas durante reunião quebra atenção e perde nuances
- Ferramentas SaaS (Otter, Fireflies, Granola) entram visivelmente na call ou enviam áudio pra cloud
- Transcrição nativa do Teams aparece pra todos os participantes ("recording on")
- Calls bilíngues (PT-BR misturado com EN) confundem ferramentas genéricas

**O que ganha:**

- Notas literais de tudo que foi dito, com timestamp e speaker
- Resumo automático com decisões, action items, follow-ups
- Histórico searchable de todas as calls
- Privacidade: áudio nunca sai do disco

---

## Decisões arquiteturais principais

### Stack

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3.11+ | Ecossistema ML/áudio mais maduro |
| Captura áudio | `sounddevice` + `soundcard` | Cross-platform, WASAPI loopback Windows |
| Transcrição | `faster-whisper` (medium-int8) | Local, qualidade alta, 2-3x realtime em CPU |
| Diarização | `pyannote.audio` 3.x | State-of-the-art pra identificar speakers |
| Resumo | Anthropic Claude (Sonnet 4) | Já está no fluxo do Rafael; prompt caching |
| UI | PyQt6 + system tray | Maduro no Windows, tray nativo |
| Storage | SQLite + markdown files | Zero-config, FTS5 pra search |
| Hotkey global | `pynput` | Cross-platform |
| Packaging | PyInstaller | `.exe` standalone |

### Princípios não-negociáveis

1. **Silenciosa** — não aparece na call, não usa bot, nem permissão do Teams
2. **Local-first** — áudio NUNCA sai da máquina
3. **Privacidade** — só o resumo (opcional) usa Claude API
4. **Sem fricção** — atalho global, system tray, auto-detect calls

### Não-objetivos (explicitamente fora de escopo)

- Bot que entra na call como participante
- Microsoft Graph API integration (exigiria admin consent)
- Capturar áudio de calls onde o usuário não está presente
- Versão cloud / SaaS
- Compartilhamento externo automatizado

---

## Estrutura final esperada

```
teams-transcript/
├── pyproject.toml
├── README.md
├── PROJECT_BRIEF.md            ← este arquivo
├── LICENSE
├── settings.example.yaml
├── src/tt/
│   ├── audio/          # WASAPI loopback + mic
│   ├── transcribe/     # whisper + pyannote + aligner
│   ├── summary/        # Claude SDK + prompts + extractors
│   ├── storage/        # SQLite + FTS5 + meetings CRUD
│   ├── ui/             # PyQt6 tray + floating window
│   ├── detection/      # Teams process monitoring
│   └── utils/
├── tests/
├── docs/
│   ├── architecture.md
│   ├── legal-ethical.md
│   ├── roadmap.md
│   └── research.md
└── scripts/
    ├── build_exe.py
    └── benchmark.py
```

---

## Roadmap em fases

MVP estimado: **7-10 dias** de trabalho focado (fases 1-5).

| Fase | Entrega | Tempo |
|---|---|---|
| 1 | Audio capture (sys + mic) → WAV | 1-2 dias |
| 2 | Transcrição offline (WAV → MD) | 1-2 dias |
| 3 | Pipeline live + UI tray + hotkey | 2-3 dias |
| 4 | Diarização + speaker labels | 1-2 dias |
| 5 | Claude integration (resumo) | 1 dia |
| 6 | Auto-detection Teams + polish | 2-3 dias |
| 7 | Search + histórico | 2 dias |
| 8 | Packaging .exe | 2-3 dias |
| 9 | macOS support | 3-4 dias |
| 10 | Integrações (Notion, Slack, etc) | varia |

Detalhes em [`docs/roadmap.md`](docs/roadmap.md).

---

## Custos

- **Setup:** ~7-10 dias dev time
- **HuggingFace token (pyannote):** grátis
- **Anthropic API:** já tem
- **Operação:** ~$0.01-0.02 por hora de transcrição (Sonnet + cache)
- **Storage:** ~10-50 MB por hora local
- **Total mensal estimado:** < $5/mês (50h de calls)

---

## Considerações legais e éticas (resumo)

| Item | Posição |
|---|---|
| LGPD (Brasil) | Single-party consent geralmente OK |
| Política Procurement Garage | ⚠️ Verificar antes de uso |
| Microsoft Teams ToS | Não proíbe captura externa |
| Recomendação default | Aviso na primeira execução; opt-in disclosure |

Templates de disclosure (PT/EN) em [`docs/legal-ethical.md`](docs/legal-ethical.md).

---

## Métricas de sucesso

- **WER (Word Error Rate):** < 15% pra PT-BR conversacional
- **Speaker accuracy:** > 85% turnos com label correto
- **Tempo de resumo:** < 30s pra 1h de transcript
- **Crash rate:** < 1 a cada 50h
- **Latência start-to-record:** < 2s

---

## Riscos identificados

| Risco | Mitigação |
|---|---|
| Whisper falha em PT+EN code-switching | Initial prompt customizado; testar large-v3 |
| Política corporativa proíbe gravação | Verificar com RH antes de uso |
| Diarização ruim em call de baixa qualidade | Fallback: sem labels, texto contínuo |
| Crash perde transcript | Append-only writer + checkpoints a cada 30s |
| GPU não disponível | CPU fallback com quantização INT8 |

---

## Próximos passos imediatos

Quando começar a implementação:

1. **Validar política Procurement Garage** — perguntar pro RH/jurídico
2. **Setup Python project** — `uv init` + deps base
3. **Implementar Fase 1** — audio capture salvando WAV
4. **Testar em call real** — gravar 5min de call interna, validar áudio
5. **Iterar fase por fase** conforme [`docs/roadmap.md`](docs/roadmap.md)

---

## Arquivos importantes

| Arquivo | Conteúdo |
|---|---|
| `README.md` | Overview + links |
| `PROJECT_BRIEF.md` | Este arquivo (resumo executivo) |
| `docs/architecture.md` | Arquitetura técnica completa (~30 páginas) |
| `docs/legal-ethical.md` | LGPD, consentimento, templates de disclosure |
| `docs/roadmap.md` | 10 fases detalhadas |
| `docs/research.md` | Comparação de libs e alternativas |
| `LICENSE` | MIT |
| `.gitignore` | Python + áudio (privacidade) |

---

## Status

**Atual (2026-05-20):** arquitetura aprovada, repo inicializado, pronto pra implementação.

**Próxima ação:** começar Fase 1 (audio capture) quando o Rafael estiver pronto.

---

**Autor:** Rafael Carrasco
**Arquitetura:** documentada com assistência do Claude (Anthropic)
**License:** MIT
