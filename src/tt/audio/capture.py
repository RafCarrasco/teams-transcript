"""Captura de áudio: loopback do sistema + microfone, misturados em WAV mono.

Fluxo de `record_to_wav`:

1. Abre dois streams de captura em paralelo, cada um na sua thread:
   - loopback (som do sistema, "o que você ouve") via `soundcard`/WASAPI;
   - microfone via `sounddevice`.
2. Cada stream alimenta seu próprio `RingBuffer` (lógica pura, testada).
3. Uma thread consumidora drena os dois buffers, mistura em mono com
   `mix_to_mono`, faz downmix para 16 kHz e grava incrementalmente num WAV.
4. A gravação roda até `Ctrl+C` (`KeyboardInterrupt`).

POR QUE 16 kHz: é a taxa que os modelos de ASR (Whisper) esperam. Gravar já
nessa taxa evita um passo de resample depois e deixa o arquivo menor.

NÃO TESTÁVEL NESTE AMBIENTE: este módulo depende de hardware de áudio e das
libs `soundcard`/`sounddevice`/`soundfile`, ausentes aqui. O código está
escrito e comentado, mas precisa de verificação manual numa máquina Windows
com áudio (ver relatório). Os imports são preguiçosos para que importar o
módulo não falhe sem essas libs — a CLI carrega `record_to_wav` sob demanda.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path

import numpy as np

from tt.audio.buffer import RingBuffer, mix_to_mono

# Tamanho do bloco lido de cada stream, em frames. ~100 ms a 48 kHz —
# equilíbrio entre latência e overhead de callback.
_BLOCK_FRAMES = 4800

# Taxa de captura nativa dos dispositivos antes do downmix para 16 kHz.
# A maioria do hardware de saída no Windows roda a 48 kHz.
_NATIVE_SAMPLE_RATE = 48000

# Capacidade dos ring buffers: ~5 s de áudio a 48 kHz. Folga suficiente para
# absorver picos de agendamento sem a thread consumidora perder dados.
_BUFFER_CAPACITY = _NATIVE_SAMPLE_RATE * 5


def record_to_wav(output: Path, sample_rate: int = 16000) -> None:
    """Grava loopback do sistema + microfone para um WAV mono, até `Ctrl+C`.

    Esta é a função chamada por `tt record`. A assinatura é estável: a CLI
    depende dela exatamente assim.

    Args:
        output: caminho do arquivo WAV a ser criado.
        sample_rate: taxa de amostragem do WAV de saída (padrão 16 kHz, a
            taxa esperada pelos modelos de transcrição).

    Levanta `AudioBackendError` se as libs de áudio não estiverem instaladas.
    """
    # Imports preguiçosos: só acontecem ao gravar de verdade, nunca no
    # `import` do módulo. _require dá um erro claro se a lib faltar.
    from tt.audio.devices import _require

    sd = _require("sounddevice")
    sc = _require("soundcard")
    sf = _require("soundfile")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Um ring buffer por fonte; preenchidos pelas threads de captura,
    # drenados pela thread consumidora.
    loopback_buffer = RingBuffer(capacity=_BUFFER_CAPACITY)
    mic_buffer = RingBuffer(capacity=_BUFFER_CAPACITY)

    # Sinaliza para todas as threads pararem (setado no KeyboardInterrupt).
    stop_event = threading.Event()
    # Coleta exceções das threads de captura para repropagar na thread main.
    errors: queue.Queue[BaseException] = queue.Queue()

    def _capture_loopback() -> None:
        """Captura o som do sistema (WASAPI loopback) para `loopback_buffer`."""
        try:
            loopback = sc.default_speaker()
            # include_loopback=True transforma a saída padrão num "microfone"
            # virtual que entrega exatamente o que está tocando.
            mic = sc.get_microphone(loopback.name, include_loopback=True)
            with mic.recorder(samplerate=_NATIVE_SAMPLE_RATE) as rec:
                while not stop_event.is_set():
                    # numframes: bloco lido por iteração. data: (frames, canais).
                    data = rec.record(numframes=_BLOCK_FRAMES)
                    # mix_to_mono colapsa canais; aqui só garantimos mono.
                    mono = data.mean(axis=1) if data.ndim == 2 else data
                    loopback_buffer.write(mono.astype(np.float32))
        except BaseException as exc:  # noqa: BLE001 - repropagado na main
            errors.put(exc)
            stop_event.set()

    def _capture_mic() -> None:
        """Captura o microfone padrão para `mic_buffer`."""
        try:
            # InputStream entrega áudio via callback noutra thread.
            def _callback(indata, frames, time_info, status):  # noqa: ANN001
                # `status` sinaliza overflow/underflow do driver — só observável.
                mono = indata.mean(axis=1) if indata.ndim == 2 else indata[:, 0]
                mic_buffer.write(np.asarray(mono, dtype=np.float32))

            with sd.InputStream(
                samplerate=_NATIVE_SAMPLE_RATE,
                channels=1,
                blocksize=_BLOCK_FRAMES,
                callback=_callback,
            ):
                # O callback faz o trabalho; aqui só esperamos o sinal de parada.
                stop_event.wait()
        except BaseException as exc:  # noqa: BLE001 - repropagado na main
            errors.put(exc)
            stop_event.set()

    # Inicia as duas capturas em paralelo.
    threads = [
        threading.Thread(target=_capture_loopback, name="capture-loopback", daemon=True),
        threading.Thread(target=_capture_mic, name="capture-mic", daemon=True),
    ]
    for t in threads:
        t.start()

    # Razão de downmix da taxa nativa para a de saída (48000/16000 = 3).
    # Decimação simples: pega 1 de cada `decim` amostras. Para qualidade
    # melhor um filtro anti-aliasing seria ideal — suficiente para ASR.
    decim = max(1, _NATIVE_SAMPLE_RATE // sample_rate)

    try:
        # WAV de saída aberto uma vez; escrito em blocos conforme o áudio chega.
        with sf.SoundFile(
            str(output),
            mode="w",
            samplerate=sample_rate,
            channels=1,
            subtype="PCM_16",
        ) as wav:
            while not stop_event.is_set():
                # Drena um bloco de cada fonte. min() alinha as fontes —
                # mix_to_mono também tolera tamanhos diferentes, mas casar
                # aqui evita acumular defasagem ao longo da gravação.
                available = min(len(loopback_buffer), len(mic_buffer))
                if available < _BLOCK_FRAMES:
                    # Ainda não há um bloco cheio nas duas fontes; aguarda.
                    stop_event.wait(timeout=0.05)
                    continue

                loop_chunk = loopback_buffer.read(available)
                mic_chunk = mic_buffer.read(available)

                # Mistura em mono sem clipping (lógica pura, testada).
                mixed = mix_to_mono(loop_chunk, mic_chunk)

                # Downmix para a taxa de saída por decimação.
                if decim > 1:
                    mixed = mixed[::decim]

                wav.write(mixed)
    except KeyboardInterrupt:
        # Ctrl+C é o jeito esperado de encerrar a gravação — não é erro.
        pass
    finally:
        # Para as threads de captura e espera elas encerrarem.
        stop_event.set()
        for t in threads:
            t.join(timeout=2.0)

    # Se uma thread de captura morreu por erro real, repropaga na main.
    if not errors.empty():
        raise errors.get()
