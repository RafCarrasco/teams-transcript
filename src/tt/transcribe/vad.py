"""Voice Activity Detection — descarta silêncio antes do Whisper.

Dropar trechos sem fala antes da transcrição economiza tempo de inferência e
reduz alucinações do Whisper em silêncio/ruído.

Dois caminhos:
- `VAD`: usa o **Silero VAD** (modelo neural), preciso, mas dependência pesada
  (lazy import — ver nota abaixo).
- `energy_gate`: fallback de **gating por energia RMS**, lógica pura em numpy,
  sem modelo. Não tão bom quanto o Silero, mas é determinístico, sempre
  disponível e **testável** aqui.

`silero-vad` não está instalada neste ambiente; o caminho neural não é
testável aqui. O caminho por energia tem cobertura de testes.
"""

from __future__ import annotations

import numpy as np
from loguru import logger

# Taxa de amostragem que o pipeline de áudio do projeto usa (16 kHz mono).
# O Silero VAD opera em 16 kHz ou 8 kHz.
DEFAULT_SAMPLE_RATE = 16_000


def energy_gate(
    audio: np.ndarray,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    frame_ms: int = 30,
    threshold: float = 0.01,
) -> np.ndarray:
    """Remove frames de baixa energia (silêncio) de um sinal de áudio.

    Fallback puro, sem ML: fatia o áudio em frames de `frame_ms`, calcula o
    RMS de cada um e mantém só os que ficam acima de `threshold`. Os frames
    sobreviventes são concatenados de volta num array contínuo.

    É uma heurística grosseira — não distingue voz de ruído de banda larga
    alto — mas é determinística e serve de rede de segurança quando o Silero
    não está disponível.

    Args:
        audio: sinal mono em float, idealmente normalizado em [-1, 1].
        sample_rate: taxa de amostragem em Hz.
        frame_ms: duração de cada frame de análise, em milissegundos.
        threshold: RMS mínimo para um frame ser considerado fala.

    Returns:
        Array só com os frames "com fala", concatenados. Se nada passar,
        retorna um array vazio com o mesmo dtype da entrada.
    """
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0:
        return audio

    frame_len = max(1, int(sample_rate * frame_ms / 1000))
    # Descarta a cauda parcial para poder remodelar em (n_frames, frame_len).
    n_frames = audio.size // frame_len
    if n_frames == 0:
        # Áudio mais curto que um frame: decide pelo RMS do sinal inteiro.
        rms = float(np.sqrt(np.mean(np.square(audio))))
        return audio if rms >= threshold else audio[:0]

    frames = audio[: n_frames * frame_len].reshape(n_frames, frame_len)
    rms = np.sqrt(np.mean(np.square(frames), axis=1))
    voiced = frames[rms >= threshold]
    return voiced.reshape(-1) if voiced.size else audio[:0]


class VAD:
    """Detector de atividade de voz baseado no Silero VAD.

    Args:
        sample_rate: taxa de amostragem do áudio de entrada (Hz).
        threshold: probabilidade mínima de fala (0-1) para o Silero marcar um
            trecho como voz. Valores maiores = mais agressivo a cortar.
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        threshold: float = 0.5,
    ) -> None:
        self.sample_rate = sample_rate
        self.threshold = threshold
        # (model, utils) do Silero — carregados sob demanda.
        self._model = None
        self._get_speech_timestamps = None

    def _load(self):
        """Carrega o modelo Silero VAD sob demanda (lazy import + cache)."""
        if self._model is not None:
            return

        try:
            # Lazy import: a extra `transcribe` traz o `silero-vad`.
            from silero_vad import get_speech_timestamps, load_silero_vad
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise ImportError(
                "silero-vad não está instalado. "
                "Instale a extra de transcrição: `uv sync --extra transcribe`."
            ) from exc

        logger.info("Carregando modelo Silero VAD")
        self._model = load_silero_vad()
        self._get_speech_timestamps = get_speech_timestamps

    def strip_silence(self, audio: np.ndarray) -> np.ndarray:
        """Remove os trechos silenciosos de um array de áudio.

        Roda o Silero VAD para achar os intervalos com fala e concatena só
        eles. O resultado vai direto para o Whisper, encurtando a inferência.

        Args:
            audio: sinal mono em float (16 kHz mono no fluxo padrão do projeto).

        Returns:
            Array contendo apenas os trechos com fala detectada. Se o Silero
            não achar fala nenhuma, devolve um array vazio.
        """
        audio = np.asarray(audio, dtype=np.float32)
        if audio.size == 0:
            return audio

        self._load()

        # O Silero precisa de um tensor torch; importado aqui (vem junto com
        # o silero-vad) para não pesar o import do módulo.
        import torch  # pragma: no cover - depende do ambiente

        tensor = torch.from_numpy(audio)
        timestamps = self._get_speech_timestamps(
            tensor,
            self._model,
            sampling_rate=self.sample_rate,
            threshold=self.threshold,
        )

        if not timestamps:
            logger.warning("Silero VAD não detectou fala no áudio")
            return audio[:0]

        # Concatena os trechos [start, end) de cada intervalo de fala.
        chunks = [audio[ts["start"] : ts["end"]] for ts in timestamps]
        stripped = np.concatenate(chunks)
        logger.info(
            "VAD: {} trechos de fala, {:.1f}s -> {:.1f}s",
            len(timestamps),
            audio.size / self.sample_rate,
            stripped.size / self.sample_rate,
        )
        return stripped
