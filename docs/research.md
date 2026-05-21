# Pesquisa: Bibliotecas e Alternativas

Avaliação técnica das opções consideradas para cada camada da stack. Documento de referência para decisões já tomadas e para futuras revisões.

---

## 1. Captura de áudio cross-platform

| Lib | Pros | Cons | Veredito |
|---|---|---|---|
| **sounddevice** | API limpa, PortAudio robusto, cross-platform | Não captura loopback (saída do sistema) sozinho | ✅ Escolhido pra mic |
| **soundcard** | Suporta loopback nativo no Windows | Menos maduro que sounddevice | ✅ Escolhido pra loopback |
| **pyaudio** | Veterano | API mais antiga, sem suporte WASAPI moderno | ❌ |
| **naudiodon** (Node) | Funciona | Ecossistema Python é mais rico | ❌ não-Python |
| **WASAPI direto** (ctypes) | Controle máximo | Complexidade enorme, código frágil | ❌ overkill |

**Stack final**: `soundcard` (loopback) + `sounddevice` (mic) + `numpy` (manipulação) + `soundfile` (I/O).

---

## 2. Transcription engine

| Engine | Tipo | Qualidade PT | Velocidade | Custo | Veredito |
|---|---|---|---|---|---|
| **faster-whisper** | Local | ✅✅✅ (medium+) | 2-3x realtime CPU | Grátis | ✅ Escolhido |
| whisper.cpp | Local | ✅✅✅ | Mais rápido C++ | Grátis | ⚠️ alternativa se perf crítica |
| OpenAI Whisper API | Cloud | ✅✅✅ | Real-time | $0.006/min = $0.36/h | ⚠️ se latência local for problema |
| AssemblyAI | Cloud | ✅✅ | Real-time | $0.12-0.65/h | ❌ caro |
| Deepgram | Cloud | ✅✅ | Real-time | $0.43/h | ❌ caro |
| Google Speech-to-Text | Cloud | ✅✅ | Real-time | $1.44/h | ❌ muito caro |
| Azure Speech | Cloud | ✅✅ | Real-time | $1.00/h | ❌ caro |
| AWS Transcribe | Cloud | ✅✅ | Real-time | $1.44/h | ❌ caro |

**Por que faster-whisper:**
- Privacidade: tudo local
- Custo zero
- Qualidade igual ao original OpenAI Whisper (mesmo modelo, motor otimizado)
- Suporta INT8 quantization → 2-3x mais rápido sem perda de qualidade perceptível
- Suporta GPU se disponível
- Maintained pela equipe SYSTRAN

**Modelo escolhido por default:** `medium-int8` (300 MB, qualidade alta, CPU OK).

---

## 3. Speaker diarization

| Lib | Qualidade | Velocidade | Setup | Veredito |
|---|---|---|---|---|
| **pyannote.audio 3.x** | ✅✅✅ State of the art | OK em CPU | HF token (grátis) | ✅ Escolhido |
| Resemblyzer | ✅✅ Boa | ✅ Rápido | Simples | ⚠️ menos preciso |
| SpeechBrain ECAPA-TDNN | ✅✅✅ | OK | Mais complexo | ⚠️ alternativa |
| NeMo (NVIDIA) | ✅✅✅ | ✅ Rápido GPU | Pesado | ❌ overkill |
| WhisperX (Whisper + pyannote bundled) | ✅✅✅ | OK | Bom | ⚠️ avaliar — pode simplificar nossa pipeline |

**Decisão:** começar com pyannote standalone porque dá controle granular. Avaliar substituir por **WhisperX** depois — ele combina transcription + diarization num pipeline único e pode ser mais simples.

---

## 4. LLM pra summary

| Provider | Modelo | Custo (input/output) | Veredito |
|---|---|---|---|
| **Google Gemini** | `gemini-2.5-flash` | **Free tier — $0** (sob rate limit) | ✅ Escolhido (grátis, cloud, sem cartão) |
| Anthropic Claude | Haiku 4 | $0.80 / $4 por 1M | ⚠️ alternativa paga; billing à parte |
| Anthropic Claude | Sonnet 4 | $3 / $15 por 1M | ⚠️ alternativa paga; melhor qualidade |
| OpenAI GPT-4o-mini | — | $0.15 / $0.60 por 1M | ⚠️ alternativa paga barata |
| Local (Llama 3.1 70B) | — | Grátis (após setup) | ❌ requer GPU forte; muita engenharia |

**Per call estimate (call de 1h ≈ 8000 tokens input + 500-1000 output):**
- Gemini 2.5 Flash (free tier): **$0/call** — dentro da cota gratuita
- gpt-4o-mini: ~$0.002/call · Haiku 4: ~$0.01/call · Sonnet 4: ~$0.03/call

**Importante — desmistificação:** assinatura ChatGPT Plus / Claude Pro ($20/mês)
**NÃO** dá acesso à API. São sistemas de billing separados — a API cobra por token,
com cartão à parte. Não existe forma oficial de usar a assinatura paga via API.
O free tier do Gemini é a única opção cloud genuinamente $0.

**Decisão:** Gemini 2.5 Flash (free tier) como default. O campo `provider` no
`settings.yaml` permite trocar pra Claude/OpenAI depois sem mudar a arquitetura.

---

## 5. UI Framework

| Framework | Pros | Cons | Veredito |
|---|---|---|---|
| **PyQt6** | Maduro, tray icon nativo, look profissional | LGPL/comercial, instalação grande | ✅ Escolhido |
| PySide6 | Idêntico ao PyQt6 mas LGPL | Idem | ⚠️ alternativa LGPL pura |
| Tkinter | Builtin | Look feio, sem tray bom | ❌ |
| Tauri (Rust + web) | UI moderna | Linguagem diferente | ❌ overhead |
| Electron | Maduro, web UI | Memória pesada | ❌ |
| pystray | Só tray icon | Limitado | ⚠️ ok pra MVP minimal |
| Web app local | HTML/CSS familiar | Precisa servidor + browser | ❌ overhead |

**Decisão:** PyQt6 (ou PySide6 se houver problema de licença) pro app completo, com pystray como fallback simples.

---

## 6. Hotkeys globais

| Lib | Windows | Mac | Linux |
|---|---|---|---|
| **pynput** | ✅ | ✅ (com permissions) | ✅ |
| keyboard | ✅ | ❌ | ⚠️ |
| global-hotkeys (PyQt) | ✅ | ✅ | ✅ |

**Decisão:** pynput primário, fallback pra Qt global hotkeys se houver conflito.

---

## 7. Storage

| Opção | Pros | Cons | Veredito |
|---|---|---|---|
| **SQLite (builtin)** + filesystem | Zero-config, FTS5 grátis | Single-user OK | ✅ Escolhido |
| DuckDB | Excelente pra analytics | Overkill | ❌ |
| Postgres | Robusto | Requer install | ❌ overkill |
| Plain markdown files only | Simples | Search ruim sem index | ❌ |

**Schema SQLite proposto:**

```sql
CREATE TABLE meetings (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP,
    duration_seconds INTEGER,
    title TEXT,
    transcript_path TEXT,
    audio_path TEXT,
    has_summary BOOLEAN,
    metadata JSON
);

CREATE VIRTUAL TABLE transcript_fts USING fts5(
    meeting_id, content,
    content_rowid=id
);
```

---

## 8. VAD (Voice Activity Detection)

| Lib | Pros | Veredito |
|---|---|---|
| **Silero VAD** | Pequeno (1MB), preciso | ✅ Escolhido |
| WebRTC VAD | Builtin em Whisper | ⚠️ ok, mas Silero é melhor |
| Auditok | Simples | ❌ |

**Uso:** dropar chunks silenciosos antes de enviar pro Whisper (economiza CPU).

---

## 9. Packaging

| Opção | Tamanho final | Setup |
|---|---|---|
| **PyInstaller** | ~150-300 MB | ✅ Maduro |
| Nuitka | Menor, mais rápido | Complexo |
| py2exe | Windows-only | Antigo |
| Docker | N/A pra app desktop | ❌ |

**Decisão:** PyInstaller. O bundle inclui Python + Whisper model + Qt = ~250 MB. Aceitável pra app que substitui SaaS de $20/mês.

---

## 10. Conclusão da pesquisa

**Stack final escolhida:**

```yaml
language: Python 3.11+
dependencies:
  audio: [sounddevice, soundcard, soundfile, numpy]
  ml: [faster-whisper, pyannote.audio, silero-vad]
  llm: [google-genai]
  ui: [PyQt6, pystray, pynput]
  utils: [typer, loguru, pydantic-settings, psutil]
  storage: sqlite (builtin) + plain markdown files
packaging: pyinstaller
testing: pytest + pytest-asyncio
ci: github actions (build .exe on tag)
```

**Trade-offs aceitos:**

- Bundle de ~300 MB (vs solução cloud "leve"): aceito pela privacidade
- CPU usage durante transcrição: aceito (Rafael tem máquina capaz)
- Setup inicial com HF token + API key: aceito (one-time)
- Sem Mac/Linux no MVP: aceito (Rafael usa Windows)
