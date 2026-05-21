# Spec — MVP: transcrição de call do Teams para .txt

- **Data:** 2026-05-21
- **Status:** Aprovado (brainstorming) — pronto para plano de implementação
- **Autor:** Rafael Carrasco

## Objetivo

Terminar uma reunião do Teams e ter um arquivo `.txt` com a transcrição no PC.
Sem fricção, sem nuvem, sem tocar no Teams.

## Problema

O plano original (PROJECT_BRIEF / docs antigos) cresceu demais: resumo via LLM,
busca em SQLite, diarização. O que o usuário realmente quer é menor: gravar a
call, transcrever local, gerar um `.txt`. Este spec define esse MVP enxuto.

## Decisões (brainstorming 2026-05-21)

1. **Output:** só `.txt` da transcrição. Sem resumo, sem nuvem, sem API key.
2. **Speakers:** rótulos `Você` (canal do microfone) e `Outros` (áudio do
   sistema). Não separa os "Outros" entre si — sem diarização (pyannote).
3. **Início:** botão flutuante — janela própria, frameless, always-on-top,
   arrastável. Aparece quando uma call do Teams é detectada. **Não** é embutido
   no Teams; é uma janela separada que flutua por cima. O Teams não é tocado.
4. **Transcrição:** roda **após** a call terminar (não ao vivo). Mais simples.
5. **Privacidade:** nada sai da máquina. A questão "resumo vs Gemini" não se
   aplica ao MVP (não há resumo).

## Escopo

**Dentro do MVP:**
- App de fundo com ícone na bandeja (system tray).
- Detecção de call do Teams.
- Botão flutuante REC/STOP.
- Captura de áudio: microfone + loopback do sistema, em **WAV estéreo**
  (canal L = mic, canal R = loopback).
- Transcrição pós-call com `faster-whisper` (local, PT/EN auto).
- Geração de `.txt` com timestamps e rótulos `Você` / `Outros`.

**Fora (pós-MVP, não implementar agora):**
- Resumo via LLM (módulo `summary/` fica dormindo no repo).
- Busca / histórico SQLite (módulo `storage/` fica dormindo no repo).
- Diarização — separar os "Outros" entre si (`transcribe/diarize.py`).
- Transcrição ao vivo / streaming.
- Empacotamento `.exe`.
- macOS.

## Arquitetura

App desktop Windows, Python, GUI em PyQt6. Uma máquina de estados controla o
ciclo de vida; PyQt fornila o event loop.

### Máquina de estados

```
IDLE ──call detectada──> CALL_DETECTED ──clique REC──> RECORDING
  ^                            │                          │
  │                            │ call sumiu               │ clique STOP
  │                            v                          │ (ou call acabou)
  └──────────────────────── (button some)                 v
  │                                                   TRANSCRIBING
  └────────────────── notificação "pronto" ◄── DONE ◄──────┘
```

- **IDLE** — sem call. Só o tray icon. Botão flutuante escondido.
- **CALL_DETECTED** — call do Teams detectada. Botão flutuante aparece: `● REC`.
- **RECORDING** — usuário clicou REC. Capturando. Botão: `■ STOP  MM:SS`.
- **TRANSCRIBING** — usuário clicou STOP (ou a call acabou). Whisper rodando em
  thread de trabalho. Botão: `Transcrevendo… ⏳`.
- **DONE** — `.txt` escrito. Notificação nativa com o caminho. Botão some;
  volta a IDLE (ou CALL_DETECTED se ainda em call).

### Fluxo de dados

```
mic ────────┐
            ├─> Recorder ─> WAV estéreo ─> Transcriber ─> segments ─> .txt
loopback ───┘   (L=mic,        (em disco)   (Whisper 2x:    (merge
                 R=loopback)                 L e depois R)   por tempo)
```

## Componentes

Cada componente tem uma responsabilidade e uma interface clara.

### `tt.app` (novo) — orquestração

Classe `App`: inicializa o Qt, o tray icon, o `CallMonitor` e o botão flutuante;
implementa a máquina de estados; conecta os sinais (call detectada → mostra
botão; clique REC → inicia `Recorder`; clique STOP → para e dispara
`Transcriber` em thread). Ponto de entrada: `tt.cli` ganha o comando `tt run`.

### `tt.ui.floating_button` (novo)

`FloatingButton(QWidget)` — frameless, `WindowStaysOnTopHint`, arrastável pela
área do widget. Um botão que muda de rótulo conforme o estado (`● REC` /
`■ STOP MM:SS` / `Transcrevendo… ⏳`). Emite sinais `rec_clicked`,
`stop_clicked`. Métodos `show_at_corner()`, `hide()`, `set_state(...)`.

### `tt.ui.tray` (novo)

`Tray(QSystemTrayIcon)` — menu: "Abrir pasta de transcrições", "Configurações"
(abre o `settings.yaml`), "Sair". Mostra notificações nativas (`showMessage`).

### `tt.detection.monitor` (novo)

`CallMonitor` — encapsula um `QTimer` que, a cada N segundos, checa
`teams.is_teams_running()` + `call_state.is_in_call(<amostra do loopback>)`.
Emite `call_started` / `call_ended`. Reusa `tt.detection.teams` e
`tt.detection.call_state` (já existem). Heurística é best-effort; refinar é
pós-MVP (issue #9).

### `tt.audio.capture` (modificar)

Hoje `record_to_wav` grava até `Ctrl+C` e mistura em mono. Trocar por uma classe
`Recorder` controlada por start/stop (o botão controla, não o Ctrl+C):
- `Recorder(output_path, sample_rate=16000)`
- `.start()` — abre as duas streams (mic + loopback) em threads, escreve um
  **WAV estéreo** (L = mic, R = loopback) de forma incremental.
- `.stop()` — encerra as streams, finaliza o arquivo.
- `.elapsed` — segundos gravados (para o label do botão).
- Escrita incremental / em blocos: se o app crashar durante a gravação, o que
  já foi gravado fica íntegro no disco.

`mix_to_mono` deixa de ser usado pelo fluxo principal (mantido no módulo para
uso futuro ou removido na implementação, a critério do plano).

### `tt.transcribe.pipeline` (modificar)

`transcribe_call(wav_path, txt_path) -> Path`:
1. Lê o WAV estéreo, separa canal L (mic) e canal R (loopback).
2. Roda `WhisperEngine.transcribe` em cada canal.
3. Marca os segments do canal mic com `speaker="Você"` e os do loopback com
   `speaker="Outros"`.
4. Funde as duas listas ordenando por `start` (reusa a lógica de
   `aligner.merge`/ordenação por timestamp).
5. Chama `txt_writer` para gerar o `.txt`.

VAD: o MVP usa o `vad_filter` embutido do `faster-whisper` (dropa silêncio sem
exigir `torch` nem `silero-vad`). O módulo `tt.transcribe.vad` (silero) não é
usado no MVP — fica para pós-MVP.

### `tt.transcribe.txt_writer` (novo)

`segments_to_txt(segments, meeting_started_at) -> str` e
`write_txt(segments, path, meeting_started_at)`. Formato definido abaixo.

### `tt.utils.config` (modificar)

Adicionar a seção `output` ao modelo de config:
- `output.dir` — pasta das transcrições. Default `~/Documents/teams-transcript`.
A seção `transcribe.model` já existe (default `medium`).

## Formato do `.txt`

```
Transcrição — 2026-05-21 14:30
──────────────────────────────
[00:00:04] Você: bom dia pessoal
[00:00:08] Outros: vamos revisar o quote do vendor
[00:00:12] Você: fechado, mando sexta
```

- Cabeçalho: `Transcrição — <data> <hora de início>` + linha separadora.
- Uma linha por segment: `[HH:MM:SS] <Você|Outros>: <texto>`.
- Timestamp relativo ao início da gravação.
- Codificação UTF-8.
- Nome do arquivo: `transcricao_AAAA-MM-DD_HHMM.txt`, na pasta `output.dir`.

## Configuração (`settings.yaml`)

```yaml
output:
  dir: ~/Documents/teams-transcript

transcribe:
  model: medium          # tiny|base|small|medium|large-v3 — menor = mais rápido
  compute_type: int8
  device: auto
  language: auto

detection:
  poll_interval_seconds: 5

ui:
  button_corner: bottom-right   # canto inicial do botão flutuante
```

As seções `summary`, `storage`, `diarization` permanecem no
`settings.example.yaml` (uso pós-MVP) mas não são lidas pelo MVP.

## Tratamento de erros

- **Sem dispositivo de loopback / mic** — o botão mostra erro curto; o tray
  notifica. O app não quebra.
- **Modelo Whisper ausente** — `faster-whisper` baixa na primeira vez
  (mostrar "baixando modelo…" no botão).
- **Crash durante a gravação** — WAV escrito de forma incremental; o trecho já
  gravado sobrevive.
- **Falha na transcrição** — manter o WAV no disco; notificar o erro; não
  apagar a gravação.
- **Call acaba durante RECORDING** — `CallMonitor.call_ended` força o STOP
  automaticamente e segue para TRANSCRIBING.

## Testes

Lógica pura — testes automatizados (pytest):
- `txt_writer`: formatação do cabeçalho, das linhas, do timestamp; UTF-8.
- Separação de canais L/R de um WAV estéreo sintético.
- Merge das duas listas de segments por timestamp (ordem correta, rótulos).
- Transições da máquina de estados de `tt.app` (sem Qt — lógica isolável).
- Config: nova seção `output` com defaults e expansão de `~`.

Não verificável neste ambiente (sem hardware de áudio, sem modelo, sem call) —
exige verificação manual numa máquina Windows:
- Captura WASAPI loopback + mic reais e o WAV estéreo resultante.
- Transcrição com modelo Whisper real (qualidade PT-BR, code-switching).
- Botão flutuante: aparição, always-on-top sobre o Teams, arraste.
- Detecção de call de verdade.
- Fluxo ponta a ponta: entrar em call → REC → STOP → `.txt`.

## Impacto no código existente (PR #1)

- `audio/capture.py` — `record_to_wav` (mono, até Ctrl+C) → classe `Recorder`
  (estéreo, start/stop). Mudança significativa.
- `transcribe/pipeline.py` — `transcribe_file` → `transcribe_call` (2 canais,
  merge, saída `.txt`). Mudança significativa.
- `transcribe/aligner.py` — reusado para o merge por timestamp.
- `utils/config.py` — nova seção `output`. Mudança pequena.
- `cli.py` — novo comando `tt run`; comandos antigos (`summarize`, `search`)
  podem ficar como estão (apontam para módulos pós-MVP).
- `summary/*`, `storage/*` — intactos, sem uso no MVP.
- `audio/buffer.py`, `audio/devices.py`, `detection/teams.py`,
  `detection/call_state.py`, `utils/logging.py`, `utils/paths.py`,
  `transcribe/whisper_engine.py` — reusados como estão.

## Critério de pronto

- `tt run` abre o app na bandeja.
- Entrar numa call do Teams faz o botão flutuante aparecer.
- REC → STOP gera um `.txt` legível na pasta configurada, com rótulos
  `Você` / `Outros` e timestamps.
- Testes de lógica pura passando; verificação manual em call real registrada.
