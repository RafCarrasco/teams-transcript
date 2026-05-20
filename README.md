# Teams Transcript — Transcrição silenciosa de calls

> **Status:** Arquitetura aprovada · pronto para implementação
> **Autor:** Rafael Carrasco
> **Data:** 2026-05-20

Ferramenta local que transcreve chamadas do Microsoft Teams **sem entrar na call e sem aparecer pra ninguém**. Captura o áudio do sistema (o que você ouve) e do microfone (o que você fala), transcreve com Whisper local, separa quem disse o quê, e gera um resumo com action items via Claude.

## Princípios

1. **Silenciosa** — não aparece na call, não usa bot, não pede permissão pro Teams
2. **Local-first** — toda transcrição roda na sua máquina; só o resumo (opcional) usa Claude API
3. **Privacidade** — áudio nunca sai do disco; transcripts em markdown local com SQLite pra search
4. **Sem fricção** — atalho global, system tray, zero-config após setup
5. **Bilíngue** — Whisper detecta PT/EN automaticamente, lida com calls mistas

## Documentação

- [`docs/architecture.md`](docs/architecture.md) — arquitetura técnica completa
- [`docs/legal-ethical.md`](docs/legal-ethical.md) — LGPD, consentimento, políticas corporativas
- [`docs/roadmap.md`](docs/roadmap.md) — fases de implementação
- [`docs/research.md`](docs/research.md) — bibliotecas e alternativas avaliadas
