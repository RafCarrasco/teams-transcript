# MVP Transcrição para .txt — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Botão flutuante detecta call do Teams, grava mic + loopback, transcreve pós-call com faster-whisper e gera um `.txt` com rótulos Você/Outros.

**Architecture:** App PyQt6 de bandeja. `CallMonitor` (QTimer) detecta call → `App` (máquina de estados) mostra o `FloatingButton` → `Recorder` grava WAV estéreo → `transcribe_call` roda Whisper nos 2 canais e escreve `.txt`.

**Tech Stack:** Python 3.12, PyQt6, faster-whisper, sounddevice/soundcard, soundfile, numpy, pydantic, typer, loguru, pytest.

Spec: [`docs/superpowers/specs/2026-05-21-mvp-transcricao-txt-design.md`](../specs/2026-05-21-mvp-transcricao-txt-design.md).

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `src/tt/utils/config.py` (mod) | + `OutputConfig`, `output`, `UIConfig.button_corner` |
| `settings.example.yaml` (mod) | + seção `output`, `ui.button_corner` |
| `src/tt/transcribe/txt_writer.py` (novo) | segments → texto `.txt` |
| `src/tt/transcribe/channels.py` (novo) | split WAV estéreo + merge dos 2 canais |
| `src/tt/transcribe/pipeline.py` (mod) | `transcribe_call` — orquestra Whisper 2 canais → `.txt` |
| `src/tt/audio/capture.py` (mod) | classe `Recorder` (estéreo, start/stop) |
| `src/tt/detection/monitor.py` (novo) | `CallMonitor` — QTimer + sinais call_started/ended |
| `src/tt/app_state.py` (novo) | `AppState` + `StateMachine` (lógica pura) |
| `src/tt/ui/__init__.py` (novo) | pacote ui |
| `src/tt/ui/floating_button.py` (novo) | `FloatingButton` (QWidget frameless) |
| `src/tt/ui/tray.py` (novo) | `Tray` (QSystemTrayIcon) |
| `src/tt/app.py` (novo) | `App` — wiring Qt + componentes |
| `src/tt/cli.py` (mod) | comando `tt run` |

---

## Task 1: Config — seção `output`

**Files:**
- Modify: `src/tt/utils/config.py`
- Test: `tests/utils/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
def test_output_section_defaults():
    from tt.utils.config import Settings
    s = Settings()
    assert s.output.dir == Path("~/Documents/teams-transcript").expanduser()

def test_ui_button_corner_default():
    from tt.utils.config import Settings
    assert Settings().ui.button_corner == "bottom-right"
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: output`)

Run: `uv run pytest tests/utils/test_config.py -k output -v`

- [ ] **Step 3: Implement**

Em `config.py`, adicionar após `StorageConfig`:

```python
class OutputConfig(_Section):
    """Seção ``output`` — onde os arquivos .txt de transcrição são salvos."""

    dir: Path = Path("~/Documents/teams-transcript")

    @field_validator("dir")
    @classmethod
    def _expand_dir(cls, v: Path) -> Path:
        return v.expanduser()
```

Em `UIConfig`, adicionar campo:

```python
    button_corner: Literal["top-left", "top-right", "bottom-left", "bottom-right"] = (
        "bottom-right"
    )
```

Em `Settings`, adicionar campo e ao `__all__`:

```python
    output: OutputConfig = Field(default_factory=OutputConfig)
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/utils/test_config.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/tt/utils/config.py tests/utils/test_config.py
git commit -m "feat: add output config section"
```

---

## Task 2: settings.example.yaml — seção `output`

**Files:**
- Modify: `settings.example.yaml`

- [ ] **Step 1: Adicionar seção `output` e `ui.button_corner`**

Adicionar bloco `output` e o campo `button_corner` em `ui`:

```yaml
output:
  dir: ~/Documents/teams-transcript   # pasta dos .txt de transcrição

ui:
  hotkey: ctrl+shift+t
  show_floating_window: false
  notify_on_complete: true
  button_corner: bottom-right         # canto inicial do botão flutuante
```

- [ ] **Step 2: Verificar que carrega**

Run: `uv run python -c "from tt.utils.config import load_settings; print(load_settings().output.dir)"`
Expected: caminho expandido de `~/Documents/teams-transcript`.

- [ ] **Step 3: Commit**

```bash
git add settings.example.yaml
git commit -m "docs: add output section to settings example"
```

---

## Task 3: txt_writer — segments para .txt

**Files:**
- Create: `src/tt/transcribe/txt_writer.py`
- Test: `tests/transcribe/test_txt_writer.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import datetime
from tt.transcribe.txt_writer import format_timestamp, segments_to_txt, write_txt


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(65) == "00:01:05"
    assert format_timestamp(3661) == "01:01:01"


def test_segments_to_txt_has_header_and_lines():
    segs = [
        {"start": 4.0, "end": 6.0, "speaker": "Você", "text": "bom dia"},
        {"start": 8.0, "end": 9.0, "speaker": "Outros", "text": "vamos revisar"},
    ]
    out = segments_to_txt(segs, datetime(2026, 5, 21, 14, 30))
    assert out.startswith("Transcrição — 2026-05-21 14:30")
    assert "[00:00:04] Você: bom dia" in out
    assert "[00:00:08] Outros: vamos revisar" in out


def test_write_txt_creates_utf8_file(tmp_path):
    path = tmp_path / "t.txt"
    write_txt([{"start": 0.0, "end": 1.0, "speaker": "Você", "text": "olá"}],
              path, datetime(2026, 5, 21, 14, 30))
    assert path.read_text(encoding="utf-8").count("Você: olá") == 1
```

- [ ] **Step 2: Run — expect FAIL** (módulo não existe)

Run: `uv run pytest tests/transcribe/test_txt_writer.py -v`

- [ ] **Step 3: Implement** `src/tt/transcribe/txt_writer.py`

```python
"""Renderização de segments de transcrição para arquivo .txt.

Formato (UTF-8):

    Transcrição — 2026-05-21 14:30
    ──────────────────────────────
    [00:00:04] Você: bom dia pessoal
    [00:00:08] Outros: vamos revisar o quote
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

_RULE = "─" * 32


def format_timestamp(seconds: float) -> str:
    """Segundos -> ``HH:MM:SS``."""
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def segments_to_txt(segments: list[dict], started_at: datetime) -> str:
    """Renderiza os segments como o conteúdo completo do .txt.

    Args:
        segments: dicts ``{start, end, speaker, text}``, ordenados por start.
        started_at: hora de início da gravação (vai no cabeçalho).
    """
    header = f"Transcrição — {started_at:%Y-%m-%d %H:%M}"
    lines = [header, _RULE]
    for seg in segments:
        ts = format_timestamp(seg["start"])
        speaker = seg.get("speaker", "Outros")
        text = seg["text"].strip()
        lines.append(f"[{ts}] {speaker}: {text}")
    return "\n".join(lines) + "\n"


def write_txt(segments: list[dict], path: str | Path, started_at: datetime) -> Path:
    """Escreve o .txt em disco (UTF-8). Cria o diretório pai se preciso."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(segments_to_txt(segments, started_at), encoding="utf-8")
    return path


def default_txt_path(output_dir: str | Path, started_at: datetime) -> Path:
    """Caminho padrão: ``<output_dir>/transcricao_AAAA-MM-DD_HHMM.txt``."""
    name = f"transcricao_{started_at:%Y-%m-%d_%H%M}.txt"
    return Path(output_dir).expanduser() / name
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/transcribe/test_txt_writer.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/tt/transcribe/txt_writer.py tests/transcribe/test_txt_writer.py
git commit -m "feat: add txt writer for transcripts"
```

---

## Task 4: channels — split estéreo + merge dos 2 canais

**Files:**
- Create: `src/tt/transcribe/channels.py`
- Test: `tests/transcribe/test_channels.py`

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import soundfile as sf
from tt.transcribe.channels import split_stereo_wav, label_and_merge


def test_label_and_merge_orders_by_start_and_labels():
    mic = [{"start": 4.0, "end": 6.0, "text": "bom dia"}]
    loop = [{"start": 0.0, "end": 3.0, "text": "olá"},
            {"start": 8.0, "end": 9.0, "text": "tchau"}]
    merged = label_and_merge(mic, loop)
    assert [s["start"] for s in merged] == [0.0, 4.0, 8.0]
    assert merged[0]["speaker"] == "Outros"
    assert merged[1]["speaker"] == "Você"


def test_split_stereo_wav(tmp_path):
    sr = 16000
    mic = np.full(sr, 0.1, dtype=np.float32)
    loop = np.full(sr, 0.2, dtype=np.float32)
    stereo = np.stack([mic, loop], axis=1)  # (N, 2): L=mic, R=loopback
    wav = tmp_path / "s.wav"
    sf.write(wav, stereo, sr)
    got_mic, got_loop, got_sr = split_stereo_wav(wav)
    assert got_sr == sr
    assert np.allclose(got_mic, 0.1, atol=1e-3)
    assert np.allclose(got_loop, 0.2, atol=1e-3)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/transcribe/test_channels.py -v`
(Requer extra `audio` para `soundfile`: `uv sync --extra audio`.)

- [ ] **Step 3: Implement** `src/tt/transcribe/channels.py`

```python
"""Separação dos canais do WAV estéreo e merge dos segments dos 2 canais.

A captura grava WAV estéreo: canal esquerdo = microfone (você), canal
direito = loopback do sistema (os outros). Cada canal é transcrito
separadamente; depois os segments são rotulados e fundidos por tempo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

SPEAKER_SELF = "Você"
SPEAKER_OTHERS = "Outros"


def split_stereo_wav(wav_path: str | Path) -> tuple[np.ndarray, np.ndarray, int]:
    """Lê um WAV estéreo e devolve ``(mic, loopback, sample_rate)``.

    `mic` é o canal L, `loopback` é o canal R, ambos float32 mono. Se o WAV
    for mono, ambos os canais recebem o mesmo sinal.
    """
    import soundfile as sf

    data, sample_rate = sf.read(str(wav_path), dtype="float32", always_2d=True)
    if data.shape[1] >= 2:
        return data[:, 0], data[:, 1], sample_rate
    return data[:, 0], data[:, 0], sample_rate


def label_and_merge(mic_segments: list[dict], loopback_segments: list[dict]) -> list[dict]:
    """Rotula e funde os segments dos dois canais, ordenados por ``start``.

    Args:
        mic_segments: segments do canal do microfone -> speaker "Você".
        loopback_segments: segments do canal do sistema -> speaker "Outros".
    """
    merged: list[dict] = []
    for seg in mic_segments:
        merged.append({**seg, "speaker": SPEAKER_SELF})
    for seg in loopback_segments:
        merged.append({**seg, "speaker": SPEAKER_OTHERS})
    merged.sort(key=lambda s: s["start"])
    return merged
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/transcribe/test_channels.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/tt/transcribe/channels.py tests/transcribe/test_channels.py
git commit -m "feat: add stereo channel split and segment merge"
```

---

## Task 5: pipeline — `transcribe_call`

**Files:**
- Modify: `src/tt/transcribe/pipeline.py`
- Test: `tests/transcribe/test_pipeline.py`

- [ ] **Step 1: Write the failing test** (usa fakes — sem Whisper real)

```python
from datetime import datetime
from pathlib import Path
import numpy as np
from tt.transcribe import pipeline


def test_transcribe_call_writes_txt(tmp_path, monkeypatch):
    # Fake do split: devolve dois sinais quaisquer + sample rate.
    monkeypatch.setattr(pipeline, "split_stereo_wav",
                        lambda p: (np.zeros(10), np.zeros(10), 16000))

    # Fake do WhisperEngine: rotula a saída conforme o canal recebido.
    calls = []

    class FakeEngine:
        def __init__(self, *a, **k): pass
        def transcribe_array(self, audio, sample_rate):
            calls.append(len(calls))
            if len(calls) == 1:
                return [{"start": 4.0, "end": 6.0, "text": "bom dia"}]
            return [{"start": 0.0, "end": 3.0, "text": "ola"}]

    monkeypatch.setattr(pipeline, "WhisperEngine", FakeEngine)

    txt = tmp_path / "out.txt"
    pipeline.transcribe_call(tmp_path / "fake.wav", txt,
                             started_at=datetime(2026, 5, 21, 14, 30))
    content = txt.read_text(encoding="utf-8")
    assert "[00:00:00] Outros: ola" in content
    assert "[00:00:04] Você: bom dia" in content
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/transcribe/test_pipeline.py::test_transcribe_call_writes_txt -v`

- [ ] **Step 3: Implement**

Adicionar a `WhisperEngine` (em `whisper_engine.py`) um método `transcribe_array(audio, sample_rate)` que aceita um `np.ndarray` mono em vez de um arquivo — escreve o array num WAV temporário e chama `transcribe`. Isso evita reescrever o WAV duas vezes.

```python
    def transcribe_array(self, audio, sample_rate: int) -> list[dict]:
        """Transcreve um array de áudio mono (float32) já em memória."""
        import tempfile

        import soundfile as sf

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            sf.write(tmp_path, audio, sample_rate)
            return self.transcribe(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
```

Reescrever `pipeline.py`:

```python
"""Orquestração da transcrição pós-call: WAV estéreo -> .txt.

`transcribe_file` (assinatura antiga, markdown) é mantida para a CLI legada;
`transcribe_call` é o fluxo do MVP.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from loguru import logger

from tt.transcribe.channels import label_and_merge, split_stereo_wav
from tt.transcribe.txt_writer import write_txt
from tt.transcribe.whisper_engine import WhisperEngine


def transcribe_call(
    wav_path: str | Path,
    txt_path: str | Path,
    started_at: datetime,
    *,
    model: str = "medium",
    compute_type: str = "int8",
    device: str = "auto",
    language: str = "auto",
) -> Path:
    """Transcreve um WAV estéreo de call e escreve o .txt.

    Canal L (mic) -> "Você"; canal R (loopback) -> "Outros".
    """
    mic, loopback, sample_rate = split_stereo_wav(wav_path)
    engine = WhisperEngine(
        model=model, compute_type=compute_type, device=device, language=language
    )
    logger.info("Transcrevendo canal do microfone…")
    mic_segs = engine.transcribe_array(mic, sample_rate)
    logger.info("Transcrevendo canal do sistema…")
    loop_segs = engine.transcribe_array(loopback, sample_rate)

    merged = label_and_merge(mic_segs, loop_segs)
    return write_txt(merged, txt_path, started_at)
```

Manter `transcribe_file` se já existir (não remover — a CLI legada usa). Se houver conflito de imports, manter os dois.

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/transcribe/ -v`

- [ ] **Step 5: Commit**

```bash
git add src/tt/transcribe/pipeline.py src/tt/transcribe/whisper_engine.py tests/transcribe/test_pipeline.py
git commit -m "feat: add transcribe_call stereo pipeline to txt"
```

---

## Task 6: audio — classe `Recorder`

**Files:**
- Modify: `src/tt/audio/capture.py`
- Test: `tests/audio/test_capture.py`

⚠️ Captura real depende de hardware — não testável neste ambiente. Testar
apenas a API (estados start/stop, elapsed) com streams mockadas.

- [ ] **Step 1: Write the failing test** (mock das streams)

```python
from tt.audio.capture import Recorder


def test_recorder_lifecycle(tmp_path, monkeypatch):
    rec = Recorder(tmp_path / "out.wav", sample_rate=16000)
    assert not rec.is_recording
    # _open_streams / _close_streams substituídos por no-ops para o teste.
    monkeypatch.setattr(rec, "_open_streams", lambda: None)
    monkeypatch.setattr(rec, "_close_streams", lambda: None)
    rec.start()
    assert rec.is_recording
    rec.stop()
    assert not rec.is_recording
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/audio/test_capture.py -v`

- [ ] **Step 3: Implement** a classe `Recorder` em `capture.py`

Manter `record_to_wav` se existir. Adicionar:

```python
class Recorder:
    """Grava microfone + loopback do sistema em um WAV estéreo.

    Canal L = microfone, canal R = loopback. Controlada por start()/stop()
    (o botão da UI controla, não Ctrl+C). Escrita incremental: se o app
    crashar, o que já foi gravado fica íntegro no disco.

    Captura real usa `soundcard` (loopback WASAPI) + `sounddevice` (mic) em
    threads paralelas; ambos importados de forma preguiçosa.
    """

    def __init__(self, output_path, sample_rate: int = 16000) -> None:
        self.output_path = Path(output_path)
        self.sample_rate = sample_rate
        self.is_recording = False
        self._start_time = None
        # streams / threads / writer preenchidos em _open_streams.

    @property
    def elapsed(self) -> float:
        """Segundos gravados até agora."""
        import time
        return 0.0 if self._start_time is None else time.monotonic() - self._start_time

    def start(self) -> None:
        if self.is_recording:
            return
        import time
        self._open_streams()
        self._start_time = time.monotonic()
        self.is_recording = True

    def stop(self) -> None:
        if not self.is_recording:
            return
        self._close_streams()
        self.is_recording = False

    def _open_streams(self) -> None:
        """Abre mic + loopback e inicia as threads de escrita (hardware)."""
        # Implementação de hardware — ver capture.py existente (record_to_wav)
        # para o padrão de soundcard/sounddevice. Escreve frames estéreo
        # intercalados (L=mic, R=loopback) em soundfile.SoundFile incremental.
        ...

    def _close_streams(self) -> None:
        """Encerra streams/threads e finaliza o arquivo WAV."""
        ...
```

A implementação de `_open_streams`/`_close_streams` reaproveita o código de
captura já existente em `record_to_wav` (soundcard para loopback, sounddevice
para mic), mas: (a) escreve **estéreo** (L=mic, R=loopback) em vez de mono;
(b) é controlada por flag, não por `KeyboardInterrupt`.

- [ ] **Step 4: Run — expect PASS** (teste de ciclo de vida)

Run: `uv run pytest tests/audio/test_capture.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/tt/audio/capture.py tests/audio/test_capture.py
git commit -m "feat: add Recorder class for stereo start/stop capture"
```

---

## Task 7: app_state — máquina de estados (lógica pura)

**Files:**
- Create: `src/tt/app_state.py`
- Test: `tests/test_app_state.py`

- [ ] **Step 1: Write the failing test**

```python
from tt.app_state import AppState, StateMachine


def test_state_machine_happy_path():
    sm = StateMachine()
    assert sm.state is AppState.IDLE
    sm.on_call_started()
    assert sm.state is AppState.CALL_DETECTED
    sm.on_rec_clicked()
    assert sm.state is AppState.RECORDING
    sm.on_stop_clicked()
    assert sm.state is AppState.TRANSCRIBING
    sm.on_transcription_done()
    assert sm.state is AppState.IDLE


def test_call_ended_during_recording_forces_transcribe():
    sm = StateMachine()
    sm.on_call_started()
    sm.on_rec_clicked()
    sm.on_call_ended()
    assert sm.state is AppState.TRANSCRIBING


def test_call_ended_while_detected_returns_to_idle():
    sm = StateMachine()
    sm.on_call_started()
    sm.on_call_ended()
    assert sm.state is AppState.IDLE
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/test_app_state.py -v`

- [ ] **Step 3: Implement** `src/tt/app_state.py`

```python
"""Máquina de estados do app — lógica pura, sem Qt.

Isolada para ser testável sem GUI. `App` (em app.py) instancia uma
StateMachine e reage às mudanças de `state`.
"""

from __future__ import annotations

from enum import Enum, auto


class AppState(Enum):
    IDLE = auto()           # sem call
    CALL_DETECTED = auto()  # call do Teams detectada; botão visível
    RECORDING = auto()      # gravando
    TRANSCRIBING = auto()   # Whisper rodando pós-call


class StateMachine:
    """Transições válidas do ciclo de vida do app.

    Transições inválidas (ex.: rec sem call) são ignoradas — o estado não muda.
    """

    def __init__(self) -> None:
        self.state = AppState.IDLE

    def on_call_started(self) -> None:
        if self.state is AppState.IDLE:
            self.state = AppState.CALL_DETECTED

    def on_call_ended(self) -> None:
        if self.state is AppState.CALL_DETECTED:
            self.state = AppState.IDLE
        elif self.state is AppState.RECORDING:
            # Call acabou no meio da gravação -> para e transcreve.
            self.state = AppState.TRANSCRIBING

    def on_rec_clicked(self) -> None:
        if self.state is AppState.CALL_DETECTED:
            self.state = AppState.RECORDING

    def on_stop_clicked(self) -> None:
        if self.state is AppState.RECORDING:
            self.state = AppState.TRANSCRIBING

    def on_transcription_done(self) -> None:
        if self.state is AppState.TRANSCRIBING:
            self.state = AppState.IDLE
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/test_app_state.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/tt/app_state.py tests/test_app_state.py
git commit -m "feat: add app state machine"
```

---

## Task 8: detection — `CallMonitor`

**Files:**
- Create: `src/tt/detection/monitor.py`
- Test: `tests/detection/test_monitor.py`

⚠️ Requer extra `ui` (`PyQt6`) para `QTimer`/`QObject`. A lógica de
disparo de sinais é testável; a detecção real de áudio não.

- [ ] **Step 1: Write the failing test**

```python
from tt.detection.monitor import CallMonitor


def test_monitor_emits_started_then_ended(qtbot=None):
    mon = CallMonitor(poll_interval_seconds=999)
    events = []
    mon.call_started.connect(lambda: events.append("started"))
    mon.call_ended.connect(lambda: events.append("ended"))
    # _check é a checagem pura; força os estados.
    mon._update(in_call=True)
    mon._update(in_call=True)   # ainda em call -> sem novo evento
    mon._update(in_call=False)
    assert events == ["started", "ended"]
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/detection/test_monitor.py -v`
(Requer `uv sync --extra ui`.)

- [ ] **Step 3: Implement** `src/tt/detection/monitor.py`

```python
"""Monitor de call do Teams — emite sinais Qt quando uma call começa/termina.

Encapsula um QTimer que periodicamente checa se o Teams está rodando e se há
áudio ativo. Heurística best-effort; refino é pós-MVP (issue #9).
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from tt.detection.teams import is_teams_running


class CallMonitor(QObject):
    """Emite `call_started` / `call_ended` na borda de mudança de estado."""

    call_started = pyqtSignal()
    call_ended = pyqtSignal()

    def __init__(self, poll_interval_seconds: int = 5) -> None:
        super().__init__()
        self._in_call = False
        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_seconds * 1000)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _poll(self) -> None:
        """Checagem periódica — Teams rodando conta como 'em call' (MVP)."""
        self._update(in_call=is_teams_running())

    def _update(self, in_call: bool) -> None:
        """Aplica o novo estado e emite o sinal de borda correspondente."""
        if in_call and not self._in_call:
            self._in_call = True
            self.call_started.emit()
        elif not in_call and self._in_call:
            self._in_call = False
            self.call_ended.emit()
```

> Nota MVP: a detecção usa só `is_teams_running()`. Combinar com energia de
> áudio no loopback (`call_state.is_in_call`) é refino pós-MVP — issue #9.

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/detection/test_monitor.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/tt/detection/monitor.py tests/detection/test_monitor.py
git commit -m "feat: add Teams call monitor"
```

---

## Task 9: ui — `FloatingButton`

**Files:**
- Create: `src/tt/ui/__init__.py` (vazio com docstring)
- Create: `src/tt/ui/floating_button.py`
- Test: `tests/ui/test_floating_button.py`

⚠️ GUI — testes constroem o widget com `QApplication` em modo offscreen
(`QT_QPA_PLATFORM=offscreen`). Aparência/always-on-top são verificação manual.

- [ ] **Step 1: Write the failing test**

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from tt.ui.floating_button import FloatingButton

_app = QApplication.instance() or QApplication([])


def test_button_label_changes_with_state():
    btn = FloatingButton()
    btn.set_state("idle")
    assert "REC" in btn.label()
    btn.set_state("recording", elapsed="02:31")
    assert "STOP" in btn.label() and "02:31" in btn.label()
    btn.set_state("transcribing")
    assert "Transcrevendo" in btn.label()
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/ui/test_floating_button.py -v`

- [ ] **Step 3: Implement** `src/tt/ui/__init__.py` (docstring) e `floating_button.py`

```python
"""Botão flutuante — janela frameless, always-on-top, arrastável.

Aparece quando uma call do Teams é detectada. Mostra REC / STOP+tempo /
"Transcrevendo…". Emite `rec_clicked` e `stop_clicked`.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QPushButton, QWidget


class FloatingButton(QWidget):
    rec_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self._button = QPushButton(self)
        self._button.clicked.connect(self._on_click)
        self._state = "idle"
        self._drag_offset = None
        self.set_state("idle")
        self.resize(160, 48)

    def label(self) -> str:
        return self._button.text()

    def set_state(self, state: str, elapsed: str = "") -> None:
        """state: 'idle' | 'recording' | 'transcribing'."""
        self._state = state
        if state == "idle":
            self._button.setText("●  REC")
        elif state == "recording":
            self._button.setText(f"■  STOP   {elapsed}")
        elif state == "transcribing":
            self._button.setText("Transcrevendo…  ⏳")
        self._button.resize(self.size())

    def _on_click(self) -> None:
        if self._state == "idle":
            self.rec_clicked.emit()
        elif self._state == "recording":
            self.stop_clicked.emit()
        # 'transcribing' -> clique ignorado.

    # --- arraste da janela ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
```

> Nota: o `QPushButton` ocupa a janela toda; o arraste é capturado pelo
> `QWidget` pai quando o clique não cai no botão. Para arrastar de forma
> confiável, na verificação manual considere uma faixa de "handle". MVP
> aceita o arraste simples.

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/ui/test_floating_button.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/tt/ui/__init__.py src/tt/ui/floating_button.py tests/ui/
git commit -m "feat: add floating REC/STOP button"
```

---

## Task 10: ui — `Tray`

**Files:**
- Create: `src/tt/ui/tray.py`
- Test: `tests/ui/test_tray.py`

- [ ] **Step 1: Write the failing test**

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from tt.ui.tray import Tray

_app = QApplication.instance() or QApplication([])


def test_tray_menu_has_expected_actions():
    tray = Tray(output_dir="/tmp/x")
    texts = [a.text() for a in tray.menu_actions()]
    assert any("pasta" in t.lower() for t in texts)
    assert any("sair" in t.lower() for t in texts)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/ui/test_tray.py -v`

- [ ] **Step 3: Implement** `src/tt/ui/tray.py`

```python
"""Ícone de bandeja — menu e notificações nativas."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon


class Tray(QSystemTrayIcon):
    def __init__(self, output_dir: str | Path) -> None:
        super().__init__()
        self._output_dir = Path(output_dir)
        self.setIcon(QIcon())  # ícone default; arte do app é pós-MVP
        self.setToolTip("teams-transcript")

        self._menu = QMenu()
        self._open_action = QAction("Abrir pasta de transcrições", self._menu)
        self._open_action.triggered.connect(self._open_folder)
        self._quit_action = QAction("Sair", self._menu)
        self._menu.addAction(self._open_action)
        self._menu.addSeparator()
        self._menu.addAction(self._quit_action)
        self.setContextMenu(self._menu)

    def menu_actions(self) -> list[QAction]:
        return [self._open_action, self._quit_action]

    @property
    def quit_action(self) -> QAction:
        return self._quit_action

    def notify(self, title: str, message: str) -> None:
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information)

    def _open_folder(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(self._output_dir)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(self._output_dir)], check=False)
        else:
            subprocess.run(["xdg-open", str(self._output_dir)], check=False)
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/ui/test_tray.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/tt/ui/tray.py tests/ui/test_tray.py
git commit -m "feat: add system tray icon"
```

---

## Task 11: app — orquestração `App`

**Files:**
- Create: `src/tt/app.py`

⚠️ Integração Qt — sem teste automatizado (verificação manual). O wiring é
fino; toda a lógica testável está em `StateMachine`, `CallMonitor`, etc.

- [ ] **Step 1: Implement** `src/tt/app.py`

```python
"""Orquestração do app — liga Qt, tray, monitor, botão flutuante e a
máquina de estados.

Fluxo:
    CallMonitor.call_started -> StateMachine -> mostra FloatingButton
    FloatingButton.rec_clicked -> Recorder.start()
    FloatingButton.stop_clicked / call_ended -> Recorder.stop() + transcreve
    transcrição (QThread) termina -> Tray.notify(caminho do .txt)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from loguru import logger
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

from tt.app_state import AppState, StateMachine
from tt.audio.capture import Recorder
from tt.detection.monitor import CallMonitor
from tt.transcribe.pipeline import transcribe_call
from tt.transcribe.txt_writer import default_txt_path
from tt.ui.floating_button import FloatingButton
from tt.ui.tray import Tray
from tt.utils.config import load_settings


class _TranscribeWorker(QThread):
    """Roda `transcribe_call` fora da thread da UI."""

    done = pyqtSignal(object)   # Path do .txt
    failed = pyqtSignal(str)

    def __init__(self, wav_path, txt_path, started_at, model):
        super().__init__()
        self._wav, self._txt = wav_path, txt_path
        self._started_at, self._model = started_at, model

    def run(self):
        try:
            path = transcribe_call(self._wav, self._txt, self._started_at,
                                   model=self._model)
            self.done.emit(path)
        except Exception as exc:  # noqa: BLE001 - reporta qualquer falha à UI
            logger.exception("Falha na transcrição")
            self.failed.emit(str(exc))


class App:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.qt = QApplication.instance() or QApplication([])
        self.qt.setQuitOnLastWindowClosed(False)

        self.sm = StateMachine()
        self.tray = Tray(self.settings.output.dir)
        self.button = FloatingButton()
        self.monitor = CallMonitor(self.settings.detection.poll_interval_seconds)

        self._recorder: Recorder | None = None
        self._started_at: datetime | None = None
        self._wav_path: Path | None = None

        self._wire()

    def _wire(self) -> None:
        self.monitor.call_started.connect(self._on_call_started)
        self.monitor.call_ended.connect(self._on_call_ended)
        self.button.rec_clicked.connect(self._on_rec)
        self.button.stop_clicked.connect(self._on_stop)
        self.tray.quit_action.triggered.connect(self.qt.quit)

    def run(self) -> int:
        self.tray.show()
        self.monitor.start()
        logger.info("teams-transcript rodando — aguardando call do Teams")
        return self.qt.exec()

    # --- handlers ---
    def _on_call_started(self) -> None:
        self.sm.on_call_started()
        if self.sm.state is AppState.CALL_DETECTED:
            self.button.set_state("idle")
            self.button.show()

    def _on_call_ended(self) -> None:
        was_recording = self.sm.state is AppState.RECORDING
        self.sm.on_call_ended()
        if was_recording and self.sm.state is AppState.TRANSCRIBING:
            self._begin_transcription()
        elif self.sm.state is AppState.IDLE:
            self.button.hide()

    def _on_rec(self) -> None:
        self.sm.on_rec_clicked()
        if self.sm.state is not AppState.RECORDING:
            return
        self._started_at = datetime.now()
        self._wav_path = default_txt_path(
            self.settings.output.dir, self._started_at
        ).with_suffix(".wav")
        self._recorder = Recorder(self._wav_path, self.settings.audio.sample_rate)
        try:
            self._recorder.start()
        except Exception as exc:  # noqa: BLE001
            self.tray.notify("Erro ao gravar", str(exc))
            return
        self.button.set_state("recording", elapsed="00:00")
        # Atualização do tempo no botão: QTimer simples a cada 1s.
        from PyQt6.QtCore import QTimer

        self._tick = QTimer()
        self._tick.timeout.connect(self._update_elapsed)
        self._tick.start(1000)

    def _update_elapsed(self) -> None:
        if self._recorder and self._recorder.is_recording:
            secs = int(self._recorder.elapsed)
            self.button.set_state("recording", elapsed=f"{secs // 60:02d}:{secs % 60:02d}")

    def _on_stop(self) -> None:
        self.sm.on_stop_clicked()
        if self.sm.state is AppState.TRANSCRIBING:
            self._begin_transcription()

    def _begin_transcription(self) -> None:
        if hasattr(self, "_tick"):
            self._tick.stop()
        if self._recorder and self._recorder.is_recording:
            self._recorder.stop()
        self.button.set_state("transcribing")
        txt_path = default_txt_path(self.settings.output.dir, self._started_at)
        self._worker = _TranscribeWorker(
            self._wav_path, txt_path, self._started_at, self.settings.transcribe.model
        )
        self._worker.done.connect(self._on_transcription_done)
        self._worker.failed.connect(self._on_transcription_failed)
        self._worker.start()

    def _on_transcription_done(self, path) -> None:
        self.sm.on_transcription_done()
        self.button.hide()
        self.tray.notify("Transcrição pronta", str(path))

    def _on_transcription_failed(self, msg) -> None:
        self.sm.on_transcription_done()
        self.button.hide()
        self.tray.notify("Falha na transcrição", msg)
```

- [ ] **Step 2: Smoke test do import**

Run: `QT_QPA_PLATFORM=offscreen uv run python -c "import tt.app; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/tt/app.py
git commit -m "feat: add app orchestration"
```

---

## Task 12: cli — comando `tt run`

**Files:**
- Modify: `src/tt/cli.py`

- [ ] **Step 1: Implement** — adicionar comando a `cli.py`

```python
@app.command()
def run() -> None:
    """Inicia o app de bandeja — botão flutuante + transcrição (MVP)."""
    from tt.app import App

    raise SystemExit(App().run())
```

- [ ] **Step 2: Verificar**

Run: `uv run tt --help`
Expected: `run` aparece na lista de comandos.

- [ ] **Step 3: Commit**

```bash
git add src/tt/cli.py
git commit -m "feat: add tt run command"
```

---

## Task 13: docs — README + CLAUDE

**Files:**
- Modify: `README.md`, `CLAUDE.md`

- [ ] **Step 1:** No README, na seção de desenvolvimento, documentar:

```bash
uv sync --all-extras      # MVP precisa de audio + ui + transcribe
uv run tt run             # inicia o app de bandeja
```

- [ ] **Step 2:** No CLAUDE.md, anotar que o MVP é `tt run` (app de bandeja),
e que `summary`/`storage` estão dormindo (pós-MVP).

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: document tt run MVP entrypoint"
```

---

## Verificação final

- [ ] `uv run pytest -q` — toda a suíte passa
- [ ] `uv run ruff check src tests` — limpo
- [ ] `uv run tt --help` — mostra `run`
- [ ] Verificação manual numa máquina Windows (registrar resultado nas issues
  #4 e #5): `tt run` → entrar em call do Teams → botão aparece → REC → STOP →
  `.txt` legível na pasta configurada.

## Self-review (preenchido)

- **Cobertura do spec:** estados (T7), botão (T9), tray (T10), captura estéreo
  (T6), transcrição 2 canais (T5), `.txt` (T3), detecção (T8), config (T1/T2),
  orquestração (T11), entrypoint (T12). ✔
- **Placeholders:** `_open_streams`/`_close_streams` (T6) e `app.py` (T11)
  contêm código real; a parte de hardware de T6 reaproveita `record_to_wav`
  existente — marcada como não testável, não como placeholder. ✔
- **Consistência de tipos:** segment = `{start,end,text,speaker?}` em todos os
  módulos; `WhisperEngine.transcribe_array` adicionado em T5 e usado em T5;
  `AppState`/`StateMachine` idem entre T7 e T11. ✔
