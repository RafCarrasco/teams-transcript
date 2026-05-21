"""Orquestração da transcrição: WAV -> markdown.

`transcribe_file` é o ponto de entrada que a CLI (`tt transcribe`) chama. Junta
as etapas do módulo:

    WAV -> [VAD: corta silêncio] -> Whisper -> [diarização] -> aligner -> markdown

Cada etapa pesada importa suas libs de ML preguiçosamente, então este módulo
importa sem `faster-whisper`/`pyannote`/`silero` instalados. A *execução* de
`transcribe_file`, claro, exige a extra `transcribe`.

Renderização de markdown: tenta usar `tt.summary.formatter.segments_to_markdown`
se existir; senão cai num formatador local simples (`_fallback_markdown`). Essa
dependência é opcional de propósito — o `formatter` do subpacote `summary` pode
ainda não ter sido implementado.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from tt.transcribe.aligner import align, merge_consecutive


def _format_timestamp(seconds: float) -> str:
    """Formata segundos como ``[HH:MM:SS]`` para os cabeçalhos do markdown."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]"


def _fallback_markdown(segments: list[dict]) -> str:
    """Renderiza segments em markdown — fallback local.

    Usado quando `tt.summary.formatter.segments_to_markdown` ainda não existe.
    Formato: um parágrafo por segment, prefixado com timestamp e (se houver)
    o speaker em negrito::

        [00:00:00] **SPEAKER_00:** Bom dia pessoal.

    Args:
        segments: segments já alinhados/fundidos.

    Returns:
        Documento markdown completo, com um título.
    """
    lines = ["# Transcrição", ""]
    for seg in segments:
        ts = _format_timestamp(seg["start"])
        speaker = seg.get("speaker")
        text = seg["text"].strip()
        if speaker:
            lines.append(f"{ts} **{speaker}:** {text}")
        else:
            lines.append(f"{ts} {text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_markdown(segments: list[dict]) -> str:
    """Renderiza os segments em markdown, preferindo o formatter do `summary`.

    Mantém o módulo desacoplado: se o subpacote `summary` expuser
    `segments_to_markdown`, usamos ele (fonte única de formatação); senão,
    `_fallback_markdown` garante que `tt transcribe` funcione de forma autônoma.
    """
    try:
        from tt.summary.formatter import segments_to_markdown
    except ImportError:
        logger.debug(
            "tt.summary.formatter indisponível — usando formatador local."
        )
        return _fallback_markdown(segments)
    return segments_to_markdown(segments)


def _apply_vad(wav_path: Path) -> Path:
    """Aplica o VAD ao WAV e devolve o caminho a transcrever.

    Lê o áudio, corta o silêncio com o Silero VAD e grava um WAV temporário
    só com fala — é esse que o Whisper recebe. A leitura/escrita de áudio
    depende de `soundfile` (extra `audio`); se algo nessa cadeia faltar ou
    falhar, o VAD é **pulado** e o WAV original segue para o Whisper. O VAD é
    uma otimização, não um requisito de correção.

    Returns:
        Caminho do WAV a transcrever — o temporário sem silêncio, ou o
        original se o VAD foi pulado.
    """
    try:
        import soundfile as sf  # extra `audio`

        from tt.transcribe.vad import VAD

        audio, sample_rate = sf.read(str(wav_path), dtype="float32")
        # Garante mono — o VAD e o Whisper esperam um único canal.
        if getattr(audio, "ndim", 1) > 1:
            audio = audio.mean(axis=1)

        stripped = VAD(sample_rate=sample_rate).strip_silence(audio)
        if stripped.size == 0:
            logger.warning("VAD não encontrou fala — transcrevendo o WAV original.")
            return wav_path

        vad_path = wav_path.with_name(f"{wav_path.stem}.vad.wav")
        sf.write(str(vad_path), stripped, sample_rate)
        logger.info("VAD aplicado -> {}", vad_path)
        return vad_path
    except Exception as exc:  # noqa: BLE001 - VAD é best-effort
        logger.warning("VAD pulado ({}): transcrevendo o WAV original.", exc)
        return wav_path


def transcribe_file(
    wav_path: Path,
    output_path: Path,
    *,
    diarize: bool = True,
    hf_token: str | None = None,
    vad: bool = True,
) -> None:
    """Transcreve um WAV e escreve o resultado em markdown.

    Esta é a função que a CLI `tt transcribe` invoca. A assinatura
    ``transcribe_file(wav, output)`` é estável; os demais parâmetros são
    keyword-only e têm padrão.

    Etapas:
    1. VAD (opcional) — corta o silêncio para acelerar o Whisper.
    2. Whisper — produz os segments de texto.
    3. Diarização (opcional) — produz os turnos de speaker.
    4. Alinhamento — cola um speaker em cada segment de texto.
    5. Fusão — junta segments adjacentes do mesmo speaker.
    6. Markdown — renderiza e grava em `output_path`.

    Args:
        wav_path: WAV de entrada (16 kHz mono no fluxo padrão do projeto).
        output_path: arquivo markdown de saída.
        diarize: se ``True``, roda a diarização e atribui speakers. Se
            ``False`` (ou sem token HF), a transcrição sai sem speakers.
        hf_token: token do Hugging Face para a diarização. Vem da config
            (`diarization.huggingface_token`). Sem ele, a diarização é pulada.
        vad: se ``True``, corta o silêncio com o Silero VAD antes do Whisper.

    Returns:
        None — o efeito é escrever `output_path`.
    """
    wav_path = Path(wav_path)
    output_path = Path(output_path)
    logger.info("Iniciando transcrição de {}", wav_path)

    # 1. VAD — opcional, best-effort.
    source_wav = _apply_vad(wav_path) if vad else wav_path

    # 2. Whisper — import preguiçoso aqui dentro.
    from tt.transcribe.whisper_engine import WhisperEngine

    engine = WhisperEngine()
    segments = engine.transcribe(source_wav)

    # 3. Diarização — opcional; precisa do token HF.
    turns: list[dict] = []
    if diarize:
        if hf_token:
            from tt.transcribe.diarize import Diarizer

            turns = Diarizer(hf_token=hf_token).diarize(wav_path)
        else:
            logger.warning(
                "diarize=True mas sem token HF — pulando diarização. "
                "A transcrição sairá sem speakers."
            )

    # 4-5. Alinhamento + fusão (lógica pura). Sem `turns`, `align` devolve os
    # segments sem speaker e `merge_consecutive` funde tudo em blocos contínuos.
    aligned = align(segments, turns)
    merged = merge_consecutive(aligned)

    # 6. Markdown.
    markdown = _render_markdown(merged)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    logger.info("Transcrição escrita em {} ({} blocos)", output_path, len(merged))
