"""Wrapper de diarização de speakers — pyannote.audio.

Diarização responde "quem falou quando": fatia o áudio em *turns*, cada um com
um rótulo de speaker (`SPEAKER_00`, `SPEAKER_01`, ...). O `aligner` depois cola
esses rótulos nos segments de texto do Whisper.

`pyannote.audio` é uma dependência pesada (PyTorch + modelos) e o pipeline de
diarização exige aceitar os termos do modelo no Hugging Face e um **token HF**.
Por isso:
- o import é **preguiçoso** (só dentro de `_load_pipeline`);
- o token HF vem da config do projeto e é recebido como parâmetro do construtor.

NÃO testável aqui (requer download dos pesos e token válido). A conversão da
anotação do pyannote em `turns` é simples e fica isolada.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

# Modelo de diarização do pyannote. Requer aceitar os termos em
# huggingface.co/pyannote/speaker-diarization-3.1 e um token HF.
_PIPELINE_ID = "pyannote/speaker-diarization-3.1"


class Diarizer:
    """Diariza arquivos WAV usando o pipeline speaker-diarization do pyannote.

    O pipeline é carregado preguiçosamente na primeira chamada a `diarize` e
    reaproveitado depois (carregar baixa/instancia vários modelos).

    Args:
        hf_token: token de acesso do Hugging Face. Vem da config do projeto
            (`diarization.huggingface_token`, normalmente via `${HF_TOKEN}`).
            Obrigatório — o pyannote recusa baixar o modelo sem ele.
        max_speakers: teto opcional de speakers, repassado ao pipeline. Limita
            a clusterização e evita "speakers fantasma" em áudio ruidoso.
            `None` deixa o pyannote decidir.
        device: ``auto`` usa CUDA se disponível, senão CPU; ou force
            ``cpu``/``cuda``.
    """

    def __init__(
        self,
        hf_token: str,
        max_speakers: int | None = None,
        device: str = "auto",
    ) -> None:
        if not hf_token:
            raise ValueError(
                "Diarizer exige um token do Hugging Face "
                "(config: diarization.huggingface_token)."
            )
        self.hf_token = hf_token
        self.max_speakers = max_speakers
        self.device = device
        # pyannote.audio.Pipeline — carregado sob demanda.
        self._pipeline = None

    def _resolve_device(self):
        """Resolve `self.device` para um `torch.device` concreto."""
        import torch  # pragma: no cover - depende do ambiente

        if self.device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(self.device)

    def _load_pipeline(self):
        """Carrega o pipeline de diarização sob demanda (lazy import + cache)."""
        if self._pipeline is not None:
            return self._pipeline

        try:
            # Lazy import: a extra `transcribe` traz o `pyannote.audio`.
            from pyannote.audio import Pipeline
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise ImportError(
                "pyannote.audio não está instalado. "
                "Instale a extra de transcrição: `uv sync --extra transcribe`."
            ) from exc

        logger.info("Carregando pipeline de diarização '{}'", _PIPELINE_ID)
        pipeline = Pipeline.from_pretrained(
            _PIPELINE_ID,
            use_auth_token=self.hf_token,
        )
        if pipeline is None:  # pragma: no cover - depende do ambiente
            # `from_pretrained` devolve None quando os termos do modelo não
            # foram aceitos na conta do HF, ou o token é inválido.
            raise RuntimeError(
                f"Não foi possível carregar '{_PIPELINE_ID}'. Verifique se o "
                "token HF é válido e se você aceitou os termos do modelo em "
                f"huggingface.co/{_PIPELINE_ID}."
            )
        pipeline.to(self._resolve_device())
        self._pipeline = pipeline
        return pipeline

    def diarize(self, wav_path: str | Path) -> list[dict]:
        """Diariza um WAV e devolve a lista de turnos de fala.

        Args:
            wav_path: caminho do arquivo WAV (16 kHz mono no fluxo padrão).

        Returns:
            Lista de turnos ``{"start": float, "end": float, "speaker": str}``,
            ordenada por `start`. Os rótulos de speaker são os do pyannote
            (`SPEAKER_00`, `SPEAKER_01`, ...) — anônimos, sem nome real.
        """
        pipeline = self._load_pipeline()

        logger.info("Diarizando {}", wav_path)
        # `num_speakers`/`max_speakers` são opcionais; só passamos o teto.
        kwargs = {}
        if self.max_speakers is not None:
            kwargs["max_speakers"] = self.max_speakers
        annotation = pipeline(str(wav_path), **kwargs)

        turns: list[dict] = []
        # `itertracks(yield_label=True)` -> (segment, track_id, speaker_label).
        for segment, _track, speaker in annotation.itertracks(yield_label=True):
            turns.append(
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "speaker": str(speaker),
                }
            )

        turns.sort(key=lambda t: t["start"])
        logger.info(
            "Diarização: {} turnos, {} speakers",
            len(turns),
            len({t["speaker"] for t in turns}),
        )
        return turns
