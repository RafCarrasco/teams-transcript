# Teams Transcript — Arquitetura Técnica

**Versão:** 1.0
**Data:** 2026-05-20
**Status:** Pronto pra implementação

---

## 1. Visão geral

Aplicação desktop local que captura o áudio do Microsoft Teams sem entrar na call, transcreve em tempo real, identifica quem está falando, e gera resumo pós-call com action items.

**Cenário típico:**
1. Rafael entra numa call do Teams normalmente (como participante)
2. Ativa o app via atalho global (ou ele detecta a call e auto-inicia)
3. Durante a call, o app captura o áudio que sai dos alto-falantes (= todos os outros falando) + o microfone (= Rafael falando)
4. Transcreve em paralelo, mostra preview opcional numa janela flutuante
5. Quando a call acaba, dispara o Gemini pra gerar resumo + action items
6. Salva tudo em markdown local + indexa pra busca

**Não-objetivos (explicitamente fora de escopo):**
- ❌ Bot que entra na call como participante
- ❌ Integração via Microsoft Teams SDK / Graph API (exigiria permissões admin)
- ❌ Capturar áudio de calls onde o usuário não está presente
- ❌ Compartilhar transcrições com terceiros sem ação explícita

---

## 2. Considerações legais e éticas

**Antes de qualquer arquitetura, contexto importante** — está documentado mais a fundo em [`legal-ethical.md`](legal-ethical.md), mas o resumo:

| Item | Posição |
|---|---|
| LGPD (Brasil) | Single-party consent é geralmente OK — você pode gravar conversas das quais participa. Comunicar aos outros participantes é boa prática e às vezes obrigatório. |
| Política corporativa Procurement Garage | Verificar antes — algumas empresas proíbem gravação sem aviso, mesmo pessoal |
| Microsoft Teams ToS | Não proíbe gravação externa via captura de áudio do sistema |
| Boas práticas | Avisar aos participantes "estou usando uma ferramenta de transcrição local" |

**Recomendação default da ferramenta:** mostrar lembrete no primeiro uso pra disclosure aos participantes. Configurável via setting.

---

## 3. Requisitos

### Funcionais

| # | Req | Prioridade |
|---|---|---|
| F1 | Capturar áudio do sistema (saída) — todos os outros participantes | P0 |
| F2 | Capturar áudio do microfone — usuário | P0 |
| F3 | Sincronizar timestamps das duas streams | P0 |
| F4 | Transcrever para texto em PT-BR e EN (auto-detect) | P0 |
| F5 | Identificar quem está falando (diarização) | P1 |
| F6 | Gerar resumo + action items pós-call | P1 |
| F7 | Atalho global pra start/stop | P0 |
| F8 | System tray icon | P0 |
| F9 | Detectar processo Teams automaticamente | P2 |
| F10 | Busca em transcrições passadas | P2 |
| F11 | Exportar pra Notion / clipboard | P2 |
| F12 | Floating window com transcrição ao vivo | P3 |

### Não-funcionais

| Aspecto | Meta |
|---|---|
| Latência (live preview) | < 5s do áudio falado pro texto na tela |
| CPU durante transcrição | < 30% num laptop médio (com Whisper medium quantizado) |
| RAM | < 2GB total |
| Privacidade | Áudio NUNCA sai do disco do usuário. Só resumo (opcional) vai pro Gemini. |
| Latência (resumo) | < 30s pós-call pra 1h de transcrição |
| Armazenamento | ~10MB/h de transcrição (markdown + áudio opcional) |
| Compatibilidade | Windows 10/11 primeiro; macOS depois; Linux opcional |

---

## 4. Stack técnica

### Decisão: Python como linguagem principal

| Critério | Python | Node.js | Rust | Go |
|---|---|---|---|---|
| Ecossistema ML/áudio | ✅✅✅ Melhor | ⚠️ Limitado | ⚠️ Crescendo | ❌ Pobre |
| Whisper bindings | ✅ Nativos | ⚠️ via WASM | ✅ whisper.cpp | ⚠️ via FFI |
| Diarização (pyannote) | ✅ Nativo | ❌ | ❌ | ❌ |
| Captura áudio cross-platform | ✅ sounddevice | ⚠️ naudiodon | ✅ cpal | ⚠️ |
| Curva pra Rafael | ✅ Familiar | ✅ Familiar | ❌ Aprenderia | ⚠️ |
| Performance de inferência | ✅ Quantização int8 | ❌ | ✅ Melhor | ⚠️ |

**Veredito:** Python ganha pela combinação de ecossistema ML + áudio + LLM SDKs. Rust seria second pick se performance fosse crítica, mas Whisper já é rápido em Python com `faster-whisper`.

### Bibliotecas escolhidas

| Camada | Lib | Por quê |
|---|---|---|
| Captura de áudio | `sounddevice` + `soundfile` | Cross-platform, WASAPI no Windows, baixa latência |
| Loopback Windows | `pycaw` ou `soundcard` | Acessa saída de áudio do sistema (o que Teams toca) |
| Transcrição | `faster-whisper` | Whisper otimizado via CTranslate2, suporta GPU/CPU, INT8 |
| Diarização | `pyannote.audio` 3.x | State of the art, multi-speaker, HuggingFace token |
| LLM | `google-genai` SDK | Gemini 2.5 Flash (free tier) pra resumo pós-call |
| UI desktop | `PyQt6` | Tray icon, hotkeys, floating window — maduro no Windows |
| Hotkey global | `pynput` ou `keyboard` | Captura tecla mesmo com foco em outra janela |
| Storage | SQLite (`sqlite3` builtin) + filesystem | Sem dep externa, fácil backup |
| Logs | `loguru` | Logging bonito + arquivo rotativo |
| Config | `pydantic-settings` + YAML | Validação de schema, env vars override |
| CLI | `typer` | Tipado, autocomplete |
| Empacotamento | `pyinstaller` | Gera .exe standalone pro Windows |

---

## 5. Arquitetura de alto nível

```
┌────────────────────────────────────────────────────────────────────┐
│                       Windows (sistema do Rafael)                   │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────────┐                                              │
│   │  Teams Desktop   │ ─── toca áudio nos speakers ───┐             │
│   │  (call em curso) │                                │             │
│   └──────────────────┘                                ▼             │
│                                              ┌──────────────────┐   │
│   ┌──────────────────┐                       │ WASAPI Loopback  │   │
│   │   Microfone      │ ─── captura voz ─────►│ + Mic Input      │   │
│   │   do Rafael      │                       │ (sounddevice)    │   │
│   └──────────────────┘                       └────────┬─────────┘   │
│                                                       │             │
│                                                       ▼             │
│                                     ┌─────────────────────────────┐ │
│                                     │  Audio Ring Buffer (PCM)    │ │
│                                     │  - Mono 16kHz               │ │
│                                     │  - Chunks de 30s c/ overlap │ │
│                                     │  - Dual stream (sys + mic)  │ │
│                                     └─────────────┬───────────────┘ │
│                                                   │                 │
│                              ┌────────────────────┴─────────┐       │
│                              ▼                              ▼       │
│              ┌─────────────────────────┐   ┌─────────────────────┐  │
│              │   faster-whisper        │   │  pyannote.audio     │  │
│              │   (transcrição local)   │   │  (diarização)       │  │
│              │   medium-int8 model     │   │  speaker labels     │  │
│              └────────────┬────────────┘   └──────────┬──────────┘  │
│                           │                           │             │
│                           └────────────┬──────────────┘             │
│                                        ▼                            │
│                          ┌──────────────────────────┐               │
│                          │  Merger + Aligner        │               │
│                          │  (matches text↔speaker)  │               │
│                          └────────────┬─────────────┘               │
│                                       │                             │
│                                       ▼                             │
│                          ┌──────────────────────────┐               │
│                          │  Transcript Writer       │               │
│                          │  (incremental .md)       │               │
│                          └────────────┬─────────────┘               │
│                                       │                             │
│              ┌────────────────────────┼──────────────────────┐      │
│              ▼                        ▼                      ▼      │
│   ┌──────────────────┐  ┌──────────────────┐   ┌──────────────────┐ │
│   │ Live preview     │  │ SQLite (search)  │   │ markdown file    │ │
│   │ (floating window)│  │ FTS5 index       │   │ ~/meetings/...md │ │
│   └──────────────────┘  └──────────────────┘   └────────┬─────────┘ │
│                                                         │           │
│                                       ┌─────────────────┘           │
│                                       │ (on call end)               │
│                                       ▼                             │
│                          ┌──────────────────────────┐               │
│                          │  Gemini API              │               │
│                          │  (google-genai SDK)      │               │
│                          │  - resumo TL;DR          │               │
│                          │  - decisões              │               │
│                          │  - action items          │               │
│                          │  - follow-ups            │               │
│                          └────────────┬─────────────┘               │
│                                       │                             │
│                                       ▼                             │
│                          ┌──────────────────────────┐               │
│                          │  System Tray             │               │
│                          │  - Notificação           │               │
│                          │  - Link pro markdown     │               │
│                          └──────────────────────────┘               │
└────────────────────────────────────────────────────────────────────┘
```

---

## 6. Componentes detalhados

### 6.1 Audio Capture

**Responsabilidade:** capturar áudio do sistema + microfone como streams sincronizadas.

**Estratégia técnica (Windows):**

```python
# Pseudo-código simplificado
import sounddevice as sd
import soundcard as sc  # for loopback

# Saída do sistema (o que Teams toca)
speaker = sc.default_speaker()
loopback_mic = sc.get_microphone(speaker.name, include_loopback=True)
# Captura PCM 16kHz mono em chunks

# Microfone do Rafael
input_mic = sc.default_microphone()

# Streams paralelas com timestamps sincronizados
```

**Decisões de design:**
- 16 kHz mono é suficiente pra fala (Whisper foi treinado nesse sample rate)
- Float32 → int16 pra economizar memória
- Ring buffer de 60s pra cada stream (cobre o chunk de 30s + overlap)
- Hard sync via timestamps no system clock — drift teórico desprezível em sessões < 2h

**Edge cases:**
- Usuário muta o microfone → stream silenciosa, OK
- Outro app tomando o device → tentar reabrir, logar
- Saída de áudio muda no meio (bluetooth conecta) → fechar e reabrir loopback

### 6.2 Transcription Pipeline

**Responsabilidade:** converter PCM em texto com timestamps.

**Modelo:** `faster-whisper` com `medium` quantizado em INT8.

| Modelo | Tamanho | Velocidade (CPU) | Qualidade PT |
|---|---|---|---|
| tiny | 75 MB | 30x realtime | ⚠️ ruim |
| base | 142 MB | 16x | ⚠️ ok |
| small | 466 MB | 6x | ✅ bom |
| **medium** | **1.5 GB** | **2-3x** | **✅✅ ótimo** |
| large-v3 | 3 GB | 1x | ✅✅✅ excelente, mas exige GPU |

**Default:** `medium-int8` (300 MB quantizado, qualidade quase igual ao FP16, 2x mais rápido).

**Configurações Whisper:**
```python
model = WhisperModel("medium", compute_type="int8", device="cpu")
segments, info = model.transcribe(
    audio_chunk,
    language=None,           # auto-detect
    vad_filter=True,         # silence skip
    word_timestamps=True,    # pra alinhar com diarização
    beam_size=5,
    initial_prompt="...",    # contexto do contexto profissional do Rafael
)
```

**Initial prompt strategy:** passar um glossário do domínio do Rafael (procurement, supply chain, AI Innovation, nomes de tools como MCP, LLM) pra melhorar reconhecimento de jargão.

### 6.3 Speaker Diarization

**Responsabilidade:** dizer "isso aqui foi falado pelo Speaker 1, isso pelo Speaker 2..."

**Lib:** `pyannote.audio` versão 3.

**Fluxo:**
1. Receber chunk de áudio (30s)
2. Rodar pipeline `speaker-diarization-3.1`
3. Retornar segments `(start, end, speaker_id)`
4. Aliñar com output do Whisper via overlap de timestamps

**Identificação do usuário:**
- Voice fingerprint inicial: na primeira execução, pede pro Rafael falar 30s pra criar embedding
- Daí em diante, o speaker cujo embedding mais se aproxima do baseline = "Rafael"
- Outros speakers ficam como "Speaker 2", "Speaker 3" — usuário pode renomear na UI

**Limitação conhecida:** áudio de baixa qualidade (call de celular) reduz precisão. ~85% accuracy em condições típicas.

### 6.4 Merger + Transcript Writer

**Responsabilidade:** combinar transcript + speaker labels num único arquivo markdown.

**Output esperado:**

```markdown
# Call · 2026-01-15 14:30

**Participantes:** Rafael, Speaker 2, Speaker 3
**Duração:** 47 min
**Auto-detectado:** Português (com trechos em English)

---

## Transcrição

**[14:30:00] Rafael:** Boa tarde pessoal, podemos começar?

**[14:30:04] Speaker 2:** Bom dia Rafael, tudo certo. Hoje vamos revisar o status do projeto X.

**[14:30:12] Speaker 3:** Antes de entrar nele, queria mencionar que o vendor Y enviou a quote ontem.

[...]

---

## Resumo gerado por IA

**TL;DR:**
- [...]

**Decisões:**
- [...]

**Action items:**
- [ ] Rafael: revisar quote do vendor Y — até sexta
- [...]

**Próximos passos:**
- [...]
```

**Implementação:** writer streaming, append-only. Cada chunk transcrito adiciona ao arquivo em disco. Se app crashar, transcript fica salva até onde processou.

### 6.5 Summary Generation (Gemini)

**Responsabilidade:** pós-call, transformar transcrição bruta em insights estruturados.

**Modelo:** `gemini-2.5-flash` (free tier do Google — $0, boa qualidade pra extração de decisões PT/EN).

**Prompt structure:**

```python
SYSTEM_PROMPT = """Você é assistente que extrai insights de transcrições
de reuniões corporativas em português/inglês. Você produz outputs estruturados
e factuais, sem inferir o que não foi dito explicitamente.

Regras:
- Action items só se foram explicitamente atribuídos a alguém
- Decisões só se houve consenso ou definição clara
- Use o nome real dos speakers quando identificado
- Markdown structured output"""

USER_PROMPT = """Aqui está a transcrição da call. Extraia:

1. **TL;DR** — 3 bullets sobre o que aconteceu
2. **Decisões** — o que foi decidido, com contexto
3. **Action items** — formato: [responsável]: [tarefa] (deadline se mencionado)
4. **Pontos abertos** — questões levantadas sem resolução
5. **Follow-ups** — próximas calls / entregas mencionadas

Transcrição:
{transcript}
"""
```

**Custo:** free tier do Gemini = **$0 por call** (dentro da cota gratuita). Gemini suporta
context caching opcional, mas no free tier não há custo a economizar.

**Limite:** o free tier tem rate limit (requisições/min + cota diária de tokens). Resumo é
1 call curta pós-call, então o limite raramente é atingido em uso normal. Se exceder:
fila com retry/backoff, ou trocar `provider` pra opção paga no `settings.yaml`.

### 6.6 UI (System Tray + Optional Floating Window)

**System Tray (sempre presente):**

```
┌─────────────────────────┐
│  Teams Transcript ●     │  ← ícone na bandeja
├─────────────────────────┤
│  Status: Gravando       │
│  Duração: 12m 34s       │
│  ─────────────────────  │
│  ⏸  Pausar              │
│  ⏹  Parar e Resumir     │
│  📂  Abrir última call  │
│  🔍  Buscar histórico   │
│  ⚙️  Configurações       │
│  ─────────────────────  │
│  Sobre                  │
│  Sair                   │
└─────────────────────────┘
```

**Atalho global default:** `Ctrl+Shift+T` (Start/Stop toggle).

**Floating window (opcional, default off):**
- Pequena (300x400px), top-right do desktop
- Sempre on top
- Live transcript scrolling
- Indicador visual de quem está falando
- Pode ser arrastada / fechada sem parar a gravação

### 6.7 Auto-detection (P2)

**Estratégia:** monitorar processos do Windows pra detectar `ms-teams.exe` ativo + chamada ativa.

**Implementação:**
- `psutil` pra listar processos
- Verificar se Teams tá com janela ativa
- Detectar áudio fluindo no loopback (RMS > threshold) por 5s consecutivos = call em andamento
- Notification: "Detectada uma call. Iniciar transcrição? [Sim] [Não] [Não perguntar de novo]"

**Configurável:** pode desativar e usar só hotkey manual.

---

## 7. Estrutura de arquivos

```
teams-transcript/
├── pyproject.toml
├── README.md
├── settings.example.yaml
├── src/
│   └── tt/
│       ├── __init__.py
│       ├── __main__.py             # entrypoint: `python -m tt`
│       ├── cli.py                  # typer CLI
│       ├── config.py               # pydantic settings
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── capture.py          # WASAPI loopback + mic
│       │   ├── devices.py          # device enumeration
│       │   ├── buffer.py           # ring buffer + chunking
│       │   └── vad.py              # voice activity detection
│       ├── transcribe/
│       │   ├── __init__.py
│       │   ├── whisper_engine.py   # faster-whisper wrapper
│       │   ├── diarize.py          # pyannote
│       │   ├── aligner.py          # text + speaker merge
│       │   └── pipeline.py         # orchestration
│       ├── summary/
│       │   ├── __init__.py
│       │   ├── gemini_client.py    # google-genai SDK
│       │   ├── prompts.py          # system + user prompts
│       │   ├── extractors.py       # TL;DR, decisions, actions
│       │   └── formatter.py        # markdown rendering
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── meetings.py         # CRUD operations
│       │   ├── search.py           # SQLite FTS5
│       │   └── migrations.py       # schema versioning
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── tray.py             # pystray / PyQt6 tray
│       │   ├── window.py           # floating preview
│       │   ├── settings_ui.py      # config dialog
│       │   └── hotkeys.py          # pynput global hotkey
│       ├── detection/
│       │   ├── __init__.py
│       │   ├── teams.py            # detect Teams process
│       │   └── call_state.py       # is-in-call heuristic
│       └── utils/
│           ├── __init__.py
│           ├── logging.py
│           └── timing.py
├── tests/
│   ├── unit/
│   │   ├── test_buffer.py
│   │   ├── test_aligner.py
│   │   └── test_extractors.py
│   ├── integration/
│   │   └── test_pipeline.py
│   └── fixtures/
│       └── sample_audio.wav
├── docs/
│   ├── architecture.md             ← este arquivo
│   ├── legal-ethical.md
│   ├── roadmap.md
│   └── research.md
├── scripts/
│   ├── build_exe.py                # PyInstaller wrapper
│   └── benchmark.py                # accuracy / speed benchmarks
└── .github/
    └── workflows/
        ├── test.yml
        └── release.yml
```

---

## 8. Configuração (settings.yaml)

```yaml
# ~/.config/teams-transcript/settings.yaml

audio:
  sample_rate: 16000
  chunk_duration_seconds: 30
  chunk_overlap_seconds: 2
  vad_threshold: 0.5

transcription:
  model: medium-int8         # tiny | base | small | medium | large-v3
  device: cpu                # cpu | cuda
  language: auto             # auto | pt | en | ...
  initial_prompt: |
    Esta é uma reunião corporativa em português brasileiro com termos
    técnicos como AI, MCP, LLM, agents, procurement, supply chain,
    Flutter, Node.js, Firebase.

diarization:
  enabled: true
  user_baseline_path: ~/.config/teams-transcript/voice_baseline.wav
  max_speakers: 6
  huggingface_token: ${HF_TOKEN}

summary:
  enabled: true
  provider: google
  model: gemini-2.5-flash
  api_key: ${GEMINI_API_KEY}
  language: pt               # output language for summary
  enable_caching: false      # free tier: nada a cachear

storage:
  meetings_dir: ~/Documents/teams-transcripts
  database_path: ~/.config/teams-transcript/db.sqlite
  retention_days: 365        # 0 = forever

ui:
  hotkey: ctrl+shift+t
  show_floating_window: false
  notification_on_call_detected: true

detection:
  auto_detect_teams: true
  rms_threshold: 0.01
  detection_window_seconds: 5

privacy:
  warn_on_first_use: true
  delete_audio_after_transcription: true
  encrypt_local_storage: false   # AES via cryptography lib (P3)
```

---

## 9. Fluxo de dados completo

```
Tempo:    0s     30s    60s    90s   120s ...     fim_da_call    +5s
           |      |      |      |      |              |           |
Áudio:    [chunk1][chunk2][chunk3][chunk4][chunk5] ... [chunkN]
                  │      │      │      │              │
                  ▼      ▼      ▼      ▼              ▼
Whisper:        text1  text2  text3  text4         textN
                  │      │      │      │              │
                  └──┬───┴──────┴──────┘              │
                     ▼                                │
              [merger + writer]                       │
                     │                                │
                     ▼                                │
              transcript.md (live, append-only)       │
                     │                                │
                     │             ┌──────────────────┘
                     │             ▼
                     │      [Gemini API call]
                     │             │
                     ▼             ▼
              transcript.md ← summary.md merge
                     │
                     ▼
              SQLite index (FTS5)
                     │
                     ▼
              Notification: "Transcrição pronta"
```

**Backpressure handling:**
- Se Whisper não dá conta do throughput, audio chunks ficam na queue
- Limite: 5 chunks (= 150s buffered)
- Além disso: drop com warning no log
- Em CPU médio, com medium-int8, raramente acontece

---

## 10. Roadmap de implementação

Detalhes em [`roadmap.md`](roadmap.md), mas em resumo:

| Fase | Entrega | Tempo estimado |
|---|---|---|
| 1 | Audio capture (sys + mic), salva WAV | 1-2 dias |
| 2 | Transcrição offline (WAV → markdown) | 1-2 dias |
| 3 | Pipeline live + UI tray + hotkey | 2-3 dias |
| 4 | Diarização + speaker labels | 1-2 dias |
| 5 | Gemini integration (summary) | 1 dia |
| 6 | Auto-detection do Teams + polish | 2-3 dias |
| 7 | macOS support | 3-4 dias |
| 8 | Linux support (opcional) | 2-3 dias |

**MVP (fases 1-5):** ~7-10 dias de trabalho focado.

---

## 11. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Whisper falha em PT+EN misto (code-switching) | Média | Alto | Usar large-v3 quando GPU disponível; testar com samples reais |
| Loopback Windows muda em versões futuras do Windows | Baixa | Médio | Camada de abstração; suporte a múltiplas APIs (WASAPI / WDM) |
| Pyannote acuracidade em call de baixa qualidade | Alta | Médio | Fallback: sem diarização, só texto contínuo |
| Política corporativa proíbe gravação | Média | Alto | Warning na primeira execução; opt-in explícito |
| Free tier do Gemini atinge rate limit | Baixa | Baixo | Resumo = 1 call curta/reunião; fila + retry se exceder; opção de provider pago |
| User esquece de iniciar gravação | Alta | Médio | Auto-detection (Fase 6) |
| Crash durante gravação perde transcript | Média | Alto | Append-only writer + checkpoints SQLite a cada 30s |
| GPU CUDA não disponível | Alta (laptops) | Baixo | CPU fallback com modelo quantizado |

---

## 12. Alternativas consideradas

### Por que não usar a transcrição nativa do Teams?

- Aparece visivelmente pros outros participantes ("Transcription is on")
- Requer permissão admin em algumas orgs
- Não exporta facilmente
- Falha de privacidade: passa pelos servidores da Microsoft

### Por que não Otter / Fireflies / Granola?

- Otter/Fireflies: bot precisa entrar na call (visível)
- Granola: captura local (similar a essa proposta) mas é macOS-only e cloud-dependent
- Nenhum tem tunning fino pra contexto do Rafael (procurement, AI)
- SaaS subscription mensal

### Por que não browser extension?

- Teams desktop é a versão usada na empresa → extension não funciona
- Limitação fundamental: WebRTC só captura via `getDisplayMedia` no Chrome, que mostra prompt

### Por que não bot via Microsoft Graph API?

- Bot aparece como participante na call — violação do requisito principal
- Requer registro de app no Azure AD + admin consent
- Complexidade altíssima pra ganho zero

---

## 13. Custos estimados

### Setup inicial (one-time)
- Dev time: ~7-10 dias pra MVP (fases 1-5)
- HuggingFace token (pyannote): grátis
- Gemini API key: grátis (Google AI Studio, sem cartão)

### Operação (recorrente)
- Compute local: $0 (roda na máquina)
- Gemini API (resumos): $0 (free tier do Google)
- Storage local: ~10-50 MB por hora (markdown + opcional WAV comprimido)
- **Total mensal estimado:** ~$0/mês (free tier; custo só de storage local)

---

## 14. Métricas de sucesso

Como saber se a ferramenta tá funcionando bem:

1. **Word Error Rate (WER)** — meta: < 15% para PT-BR conversacional
2. **Speaker accuracy** — meta: > 85% dos turnos com label correto
3. **Tempo de geração de resumo** — meta: < 30s pra 1h de transcript
4. **Crash rate** — meta: < 1 crash a cada 50h de uso
5. **Latência start-to-record** — meta: < 2s do hotkey até começar a gravar

Benchmark script (`scripts/benchmark.py`) roda essas métricas contra um conjunto de calls de teste anotadas manualmente.

---

## 15. Próximos passos imediatos (quando o Rafael for começar)

1. **Confirmar requisitos com a Procurement Garage** — checar política de gravação interna
2. **Decidir nome do produto** — sugestões: `tt` (curto), `EchoNote`, `WhisperDesk`, `PaperTrail`
3. **Setup do repositório no GitHub** — privado inicialmente
4. **Setup Python project** — `pyproject.toml`, `uv` ou `poetry`
5. **Implementar Fase 1** — Audio Capture + sample WAV em 1 dia

Convidar a `executing-plans` skill quando o spec virar plan via `writing-plans`.
