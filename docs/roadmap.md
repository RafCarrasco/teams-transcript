# Roadmap de Implementação

**Status:** Planejamento inicial
**Última atualização:** 2026-05-20

Roadmap em fases de 1-3 dias cada. Cada fase termina com entregável testável e demoable.

---

## Fase 1: Audio Capture (P0)

**Objetivo:** capturar áudio do sistema + microfone e salvar em WAV.

**Entregável:**
- CLI `tt record --output meeting.wav` que grava até ser interrompido por Ctrl+C
- Arquivo WAV resultante contém 2 canais misturados (saída do sistema + mic)
- Funciona no Windows

**Tarefas:**
- [ ] Setup do projeto Python com `uv` + `pyproject.toml`
- [ ] Adicionar deps: `sounddevice`, `soundfile`, `soundcard`, `typer`, `loguru`
- [ ] Implementar `audio/devices.py` — enumerar dispositivos disponíveis
- [ ] Implementar `audio/capture.py` — captura WASAPI loopback + mic em paralelo
- [ ] Sincronizar via system clock; merge em mono 16kHz
- [ ] CLI `tt record`
- [ ] Test: gravar 5 min em call do Teams real, verificar áudio limpo

**Tempo estimado:** 1-2 dias

---

## Fase 2: Transcrição Offline (P0)

**Objetivo:** processar um WAV salvo e gerar transcript em markdown.

**Entregável:**
- CLI `tt transcribe meeting.wav --output meeting.md`
- Arquivo markdown com timestamps e texto

**Tarefas:**
- [ ] Adicionar dep: `faster-whisper`
- [ ] Download do modelo medium-int8 (~300 MB)
- [ ] Implementar `transcribe/whisper_engine.py`
- [ ] Implementar `transcribe/pipeline.py` — processar WAV → segments
- [ ] Implementar `summary/formatter.py` — segments → markdown
- [ ] CLI `tt transcribe`
- [ ] Test: transcrever sample de 30 min, validar qualidade

**Tempo estimado:** 1-2 dias

---

## Fase 3: Pipeline Live + UI Tray (P0)

**Objetivo:** gravar e transcrever em paralelo, com indicador visual.

**Entregável:**
- App standalone (não-CLI) com system tray
- Hotkey global `Ctrl+Shift+T` inicia/para gravação
- Markdown vai sendo escrito incrementalmente durante a call
- Notificação ao final: "Transcrição completa, X minutos, abrir?"

**Tarefas:**
- [ ] Adicionar deps: `PyQt6`, `pynput`
- [ ] Implementar `ui/tray.py` — tray icon, menu
- [ ] Implementar `ui/hotkeys.py` — global hotkey
- [ ] Refatorar pipeline pra streaming (chunks de 30s)
- [ ] Ring buffer entre audio capture e transcription
- [ ] Append-only writer pro markdown
- [ ] Notificação nativa Windows
- [ ] Settings dialog mínimo (output path)

**Tempo estimado:** 2-3 dias

---

## Fase 4: Diarização (P1)

**Objetivo:** identificar quem está falando.

**Entregável:**
- Transcript com labels "Rafael:", "Speaker 2:", etc.
- Setup wizard pra capturar voice baseline do Rafael

**Tarefas:**
- [ ] Adicionar dep: `pyannote.audio` + HF token
- [ ] Implementar `transcribe/diarize.py`
- [ ] Implementar `transcribe/aligner.py` — merge text + speaker
- [ ] Voice baseline capture flow (30s recording wizard)
- [ ] Cosine similarity pra identificar usuário em embeddings
- [ ] Test em call de 3+ pessoas

**Tempo estimado:** 1-2 dias

---

## Fase 5: Summary via Gemini (P1)

**Objetivo:** gerar resumo estruturado pós-call.

**Entregável:**
- Markdown final inclui seção "Resumo gerado por IA" com TL;DR, decisões, action items
- Provider plugável via `settings.yaml` (Gemini default, free tier)
- Configurable (PT vs EN output)

**Tarefas:**
- [ ] Adicionar dep: `google-genai`
- [ ] Implementar `summary/gemini_client.py`
- [ ] Implementar `summary/prompts.py` (system + user prompt)
- [ ] Implementar `summary/extractors.py` — parse output estruturado
- [ ] Integrar no flow pós-call automaticamente
- [ ] Settings: provider/model selection, API key (`GEMINI_API_KEY`)
- [ ] Test: validar qualidade do resumo em 5 calls reais

**Tempo estimado:** 1 dia

**MVP completo neste ponto:** Fases 1-5. ~7-10 dias totais.

---

## Fase 6: Auto-detection do Teams (P2)

**Objetivo:** detectar automaticamente quando Teams entrou em call e oferecer pra gravar.

**Entregável:**
- Toast notification quando call é detectada: "Gravar essa call? [Sim] [Não] [Não perguntar de novo]"

**Tarefas:**
- [ ] Adicionar dep: `psutil`
- [ ] Implementar `detection/teams.py` — Teams process monitoring
- [ ] Implementar `detection/call_state.py` — heurística "está em call" (RMS no loopback)
- [ ] Background thread no app
- [ ] Notificação acionável
- [ ] Setting: enable/disable auto-detection

**Tempo estimado:** 2-3 dias

---

## Fase 7: Search + Histórico (P2)

**Objetivo:** buscar em transcrições passadas.

**Entregável:**
- Menu "Buscar histórico" no tray abre janela com search input
- SQLite FTS5 indexado

**Tarefas:**
- [ ] Implementar `storage/search.py` — FTS5
- [ ] Implementar `storage/migrations.py` — schema versioning
- [ ] UI: search window com results
- [ ] Indexar todas as transcrições existentes na primeira execução
- [ ] Indexar incrementalmente após cada call

**Tempo estimado:** 2 dias

---

## Fase 8: Polish + Packaging (P2)

**Objetivo:** distribuir como `.exe` único.

**Tarefas:**
- [ ] `pyinstaller` config
- [ ] Icon, signing (opcional)
- [ ] Auto-update mechanism (P3, deixar pra depois)
- [ ] Install wizard / portable mode
- [ ] Crash reporting (Sentry self-hosted? ou opt-in)

**Tempo estimado:** 2-3 dias

---

## Fase 9: macOS Support (P3)

**Objetivo:** rodar em Mac.

**Notas:**
- Captura de áudio do sistema no Mac requer BlackHole ou Loopback (apps de terceiros) — barreira de adoção
- Alternativa: usar Core Audio Taps (macOS 14+) — API moderna

**Tempo estimado:** 3-4 dias

---

## Fase 10: Integrações (P3)

Ideas pra explorar quando MVP estabilizar:

- **Notion**: exportar transcript automaticamente pra uma página
- **Slack**: post de resumo no canal #meetings
- **Calendar**: vincular à reunião do Outlook/Google
- **Linear/Jira**: criar tickets a partir de action items
- **Email**: enviar resumo pros participantes (com consent)

---

## Critérios de "ready for daily use"

A ferramenta pode ser usada em produção quando:

- [x] Arquitetura aprovada
- [ ] Fases 1-5 implementadas e testadas em pelo menos 5 calls reais
- [ ] WER < 20% em PT-BR
- [ ] Sem crash em 10 horas consecutivas
- [ ] Resumo de qualidade confirmado (validation manual em 3 calls)
- [ ] Disclosure pattern definido com Rafael
- [ ] Política da empresa verificada
