# CLAUDE.md

Wrapper fino para agentes de código neste repositório.

## O que é

`teams-transcript` — app desktop (Windows-first) que transcreve calls do Teams
localmente, sem entrar na call. Pacote Python `tt` em `src/tt/`.

## Comandos principais

```bash
uv sync --extra dev          # ambiente base + ferramentas de teste
uv run pytest -q             # roda a suíte completa
uv run ruff check src tests  # lint
uv run tt --help             # CLI

# MVP — app de bandeja (precisa das 3 extras):
uv sync --extra audio --extra ui --extra transcribe
uv run tt run

# Extras: audio (sounddevice/soundcard/soundfile), ui (PyQt6/pynput),
# transcribe (faster-whisper), diarize (pyannote/silero — pós-MVP).
```

Python 3.11/3.12 (ML libs ainda não cobrem 3.13+). `uv` cuida da versão.

## MVP

O MVP é `tt run`: app de bandeja → botão flutuante detecta call do Teams →
grava mic + loopback → transcreve com faster-whisper → gera `.txt`. Sem nuvem.
Spec: [`docs/superpowers/specs/2026-05-21-mvp-transcricao-txt-design.md`](docs/superpowers/specs/2026-05-21-mvp-transcricao-txt-design.md).

Fora do MVP, **dormindo** no repo (pós-MVP): `summary/` (resumo via Gemini),
`storage/` (SQLite + busca), `transcribe/diarize.py` (pyannote).

## Arquitetura

Subpacotes em `src/tt/`: `audio` (captura WASAPI loopback + mic), `transcribe`
(Whisper + diarização + alinhamento), `summary` (resumo via Gemini, free tier),
`storage` (SQLite + FTS5), `ui` (tray PyQt6), `detection` (monitor do Teams),
`utils` (config, logging). Entry point CLI em `cli.py`.

Detalhes: [`docs/architecture.md`](docs/architecture.md).

## Convenções específicas

- **Imports pesados são lazy.** Libs de áudio/ML são importadas dentro de
  funções, não no topo do módulo — o pacote precisa importar sem os extras.
- **Privacidade é requisito, não feature.** Áudio nunca sai do disco. Só o texto
  do resumo vai para a nuvem. Logs não capturam conteúdo transcrito.
- **Provider de LLM é plugável.** Campo `provider` no `settings.yaml`. Default
  Gemini (free tier). Ver [`docs/adr/0001-llm-provider-gemini.md`](docs/adr/0001-llm-provider-gemini.md).
- TDD para lógica pura. Testes em `tests/<área>/`, cada um é pacote (`__init__.py`).

## Documentação relacionada

- [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md) — resumo executivo
- [`docs/roadmap.md`](docs/roadmap.md) — fases de implementação
- [`docs/ideas.md`](docs/ideas.md) — ideias e insights em aberto
- [`docs/legal-ethical.md`](docs/legal-ethical.md) — LGPD, consentimento
