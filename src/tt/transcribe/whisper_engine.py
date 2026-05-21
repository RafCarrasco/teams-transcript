"""Wrapper do faster-whisper — transcrição de áudio para segments de texto.

`faster_whisper` é uma dependência pesada (binários CTranslate2 + modelos de
vários GB). Para que `import tt.transcribe` funcione em ambientes sem ela —
CI de lógica pura, máquinas de dev sem GPU — o import é **preguiçoso**: só
acontece dentro de `_load_model()`, na primeira transcrição.

NÃO testável aqui com modelo real (requer download dos pesos). A lógica de
conversão de saída em segments é simples e fica isolada para inspeção.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger


class WhisperEngine:
    """Transcreve arquivos WAV usando faster-whisper.

    O modelo é carregado preguiçosamente na primeira chamada a `transcribe` e
    reaproveitado nas seguintes (carregar pesa vários segundos / GB de RAM).

    Args:
        model: tamanho do modelo Whisper — ``tiny``/``base``/``small``/
            ``medium``/``large-v3``. ``medium`` é o equilíbrio padrão do
            projeto entre qualidade e custo em CPU.
        compute_type: precisão do CTranslate2 — ``int8`` (CPU, mais leve),
            ``int8_float16`` ou ``float16`` (GPU).
        device: ``auto`` deixa o faster-whisper escolher (usa CUDA se houver),
            ou force com ``cpu``/``cuda``.
        language: ``auto`` deixa o Whisper detectar; ``pt``/``en`` fixam o
            idioma (mais rápido e estável quando você já sabe).
        initial_prompt: texto-semente passado ao decoder. Útil para
            **code-switching PT/EN**: reuniões de procurement misturam termos
            como "quote", "vendor", "lead time", "SLA". Um prompt como
            ``"Reunião de procurement. Termos: vendor, quote, SLA, lead time."``
            enviesa o modelo a grafar esses termos corretamente em vez de
            "traduzi-los" foneticamente. Também ajuda com nomes próprios.
    """

    def __init__(
        self,
        model: str = "medium",
        compute_type: str = "int8",
        device: str = "auto",
        language: str = "auto",
        initial_prompt: str | None = None,
    ) -> None:
        self.model_name = model
        self.compute_type = compute_type
        self.device = device
        self.language = language
        self.initial_prompt = initial_prompt
        # Instância de faster_whisper.WhisperModel — carregada sob demanda.
        self._model = None

    def _load_model(self):
        """Carrega o WhisperModel sob demanda (lazy import + cache).

        Mantém a instância em `self._model` para reuso. Levanta um
        `ImportError` com mensagem acionável se a extra `transcribe` não
        estiver instalada.
        """
        if self._model is not None:
            return self._model

        try:
            # Lazy import: só falha aqui, nunca no import do módulo.
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise ImportError(
                "faster-whisper não está instalado. "
                "Instale a extra de transcrição: `uv sync --extra transcribe`."
            ) from exc

        logger.info(
            "Carregando modelo Whisper '{}' (device={}, compute={})",
            self.model_name,
            self.device,
            self.compute_type,
        )
        self._model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type,
        )
        return self._model

    def transcribe(self, wav_path: str | Path) -> list[dict]:
        """Transcreve um WAV e devolve a lista de segments de texto.

        Args:
            wav_path: caminho do arquivo WAV (idealmente 16 kHz mono — formato
                que o pipeline de áudio do projeto já produz).

        Returns:
            Lista de segments ``{"start": float, "end": float, "text": str}``,
            em ordem temporal. Ainda **sem** speaker — a diarização e o
            alinhamento são etapas posteriores do pipeline.
        """
        model = self._load_model()

        # `language="auto"` -> None faz o faster-whisper detectar o idioma.
        language = None if self.language == "auto" else self.language

        logger.info("Transcrevendo {}", wav_path)
        # `segments` é um gerador preguiçoso; iterar é o que de fato roda a
        # inferência. `info` traz idioma detectado, duração etc.
        # vad_filter=True usa o VAD (Silero ONNX) embutido do faster-whisper
        # para dropar silêncio — não exige torch nem o pacote silero-vad.
        segments, info = model.transcribe(
            str(wav_path),
            language=language,
            initial_prompt=self.initial_prompt,
            vad_filter=True,
        )
        logger.debug(
            "Idioma detectado: {} (p={:.2f})",
            getattr(info, "language", "?"),
            getattr(info, "language_probability", 0.0),
        )

        result: list[dict] = []
        for seg in segments:
            text = seg.text.strip()
            if not text:
                # Pula segments vazios (silêncio que o decoder marcou sem texto).
                continue
            result.append(
                {
                    "start": float(seg.start),
                    "end": float(seg.end),
                    "text": text,
                }
            )

        logger.info("Whisper produziu {} segments", len(result))
        return result

    def transcribe_array(self, audio, sample_rate: int) -> list[dict]:
        """Transcreve um array de áudio mono (float32) já em memória.

        Conveniência para o pipeline estéreo: cada canal já está separado em
        memória, então grava-se um WAV temporário e reaproveita-se
        :meth:`transcribe`.

        Args:
            audio: array NumPy mono float32.
            sample_rate: taxa de amostragem do array, em Hz.
        """
        import tempfile

        import soundfile as sf

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            sf.write(tmp_path, audio, sample_rate)
            return self.transcribe(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
