# Teams Transcript — Transcrição silenciosa de calls

> **Status:** MVP em implementação — captura + transcrição para `.txt`
> **Autor:** Rafael Carrasco
> **Data:** 2026-05-21

Ferramenta local que transcreve chamadas do Microsoft Teams **sem entrar na call e sem aparecer pra ninguém**. Captura o áudio do sistema (o que você ouve) e do microfone (o que você fala), transcreve com Whisper local, separa quem disse o quê, e gera um resumo com action items via Gemini (free tier).

## Princípios

1. **Silenciosa** — não aparece na call, não usa bot, não pede permissão pro Teams
2. **Local-first** — toda transcrição roda na sua máquina; só o resumo (opcional) usa Gemini API (free tier)
3. **Privacidade** — áudio nunca sai do disco; transcripts em markdown local com SQLite pra search
4. **Sem fricção** — atalho global, system tray, zero-config após setup
5. **Bilíngue** — Whisper detecta PT/EN automaticamente, lida com calls mistas

## MVP — como usar

Requer [`uv`](https://docs.astral.sh/uv/) e Python 3.11/3.12.

```bash
git clone https://github.com/RafCarrasco/teams-transcript.git
cd teams-transcript

# MVP precisa das extras de áudio, UI e transcrição:
uv sync --extra audio --extra ui --extra transcribe

uv run tt run                # abre o app na bandeja
```

`tt run` deixa um ícone na bandeja. Quando uma call do Teams é detectada,
aparece um botão flutuante: **REC** começa a gravar, **STOP** encerra e gera
um `.txt` da transcrição em `~/Documents/teams-transcript/` (configurável em
`settings.yaml`).

## Desenvolvimento

```bash
uv sync --extra dev          # ambiente base + ferramentas de teste
uv run pytest -q             # roda a suíte de testes
uv run ruff check src tests  # lint
uv run tt --help             # CLI

cp settings.example.yaml settings.yaml     # ajustar configuração
```

Extras: `audio` (captura), `ui` (PyQt6), `transcribe` (faster-whisper),
`diarize` (pyannote — pós-MVP), `dev` (testes/lint). Ver [`CLAUDE.md`](CLAUDE.md).

## Documentação

- [`docs/architecture.md`](docs/architecture.md) — arquitetura técnica completa
- [`docs/legal-ethical.md`](docs/legal-ethical.md) — LGPD, consentimento, políticas corporativas
- [`docs/roadmap.md`](docs/roadmap.md) — fases de implementação
- [`docs/research.md`](docs/research.md) — bibliotecas e alternativas avaliadas
- [`docs/ideas.md`](docs/ideas.md) — ideias e insights em aberto
- [`docs/adr/`](docs/adr/) — registros de decisão de arquitetura (ADR)
