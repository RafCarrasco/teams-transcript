"""Alinhamento de transcrição × diarização — lógica pura, sem dependências de ML.

O Whisper produz *segments* de texto (start/end/text) e o pyannote produz
*turns* de fala (start/end/speaker). Estas duas linhas do tempo não estão
sincronizadas: um segment de texto pode cair em cima de um ou mais turnos de
speaker. Este módulo resolve essa correspondência.

Tudo aqui é aritmética de intervalos — testável e determinístico, sem precisar
de modelos baixados. Por isso concentra a cobertura de testes do pacote.

Formato dos dados:
    segment  -> {"start": float, "end": float, "text": str, ["speaker": str]}
    turn     -> {"start": float, "end": float, "speaker": str}
Tempos sempre em segundos.
"""

from __future__ import annotations

# Speaker atribuído a um segment de texto que não cai sobre nenhum turno de
# diarização (ex.: ruído transcrito, ou diarização que perdeu o trecho).
UNKNOWN_SPEAKER = "UNKNOWN"


def _overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    """Duração da sobreposição entre os intervalos [a] e [b], em segundos.

    Retorna 0.0 quando não há sobreposição — inclusive no caso de bordas que
    apenas se tocam (fim de um == início do outro), que não conta como fala
    em comum.
    """
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def align(
    transcription_segments: list[dict],
    diarization_turns: list[dict],
) -> list[dict]:
    """Atribui a cada segment de texto o speaker que mais se sobrepõe a ele.

    Para cada segment, soma a sobreposição temporal contra todos os turnos de
    cada speaker e escolhe o speaker com maior soma. Somar (em vez de pegar o
    maior turno isolado) é importante: a diarização costuma fragmentar a fala
    de uma pessoa em vários turnos curtos.

    Casos de borda tratados:
    - `diarization_turns` vazio: retorna os segments **sem** a chave `speaker`
      (sinaliza "diarização não rodou"); nada quebra.
    - Segment que não sobrepõe nenhum turno: recebe `speaker=UNKNOWN`.
    - Bordas que apenas se tocam: sobreposição zero (ver `_overlap`).

    Não muta os dicts de entrada — devolve cópias rasas novas.

    Args:
        transcription_segments: segments de texto do Whisper.
        diarization_turns: turnos de fala do diarizador.

    Returns:
        Lista de segments (cópias), na mesma ordem da entrada. Com diarização,
        cada um ganha a chave `speaker`; sem diarização, saem como vieram.
    """
    # Sem diarização: devolve cópias intactas, sem inventar speaker.
    if not diarization_turns:
        return [dict(seg) for seg in transcription_segments]

    aligned: list[dict] = []
    for seg in transcription_segments:
        seg_start = seg["start"]
        seg_end = seg["end"]

        # Soma de sobreposição por speaker.
        overlap_by_speaker: dict[str, float] = {}
        for turn in diarization_turns:
            ov = _overlap(seg_start, seg_end, turn["start"], turn["end"])
            if ov > 0.0:
                spk = turn["speaker"]
                overlap_by_speaker[spk] = overlap_by_speaker.get(spk, 0.0) + ov

        new_seg = dict(seg)
        if overlap_by_speaker:
            # Maior soma de sobreposição vence. Em empate, `max` mantém o
            # primeiro encontrado — determinístico para uma dada ordem.
            new_seg["speaker"] = max(overlap_by_speaker, key=overlap_by_speaker.get)
        else:
            new_seg["speaker"] = UNKNOWN_SPEAKER
        aligned.append(new_seg)

    return aligned


def merge_consecutive(segments: list[dict]) -> list[dict]:
    """Funde segments adjacentes que pertencem ao mesmo speaker.

    O Whisper fatia a fala de forma fina (cada poucos segundos). Depois do
    alinhamento, isso vira vários segments seguidos do mesmo falante. Esta
    função os consolida em blocos maiores e legíveis: um bloco por turno de
    fala contínuo.

    Regras:
    - Dois segments fundem se tiverem o mesmo `speaker` (a chave ausente conta
      como um "speaker" coerente — ex.: diarização desligada funde tudo).
    - O bloco resultante vai do `start` do primeiro ao `end` do último.
    - Os textos são unidos com um único espaço, cada trecho com strip().

    Não muta os dicts de entrada.

    Args:
        segments: segments já ordenados temporalmente (saída de `align`).

    Returns:
        Nova lista de segments fundidos.
    """
    if not segments:
        return []

    merged: list[dict] = [dict(segments[0])]
    for seg in segments[1:]:
        last = merged[-1]
        # `.get` trata ausência de 'speaker' como um valor próprio (None),
        # então segments sem speaker fundem entre si normalmente.
        if seg.get("speaker") == last.get("speaker"):
            last["end"] = seg["end"]
            last["text"] = f"{last['text'].strip()} {seg['text'].strip()}".strip()
        else:
            merged.append(dict(seg))

    # Normaliza o texto do primeiro bloco (e de blocos de um segment só),
    # que não passaram pelo join acima.
    for block in merged:
        block["text"] = block["text"].strip()

    return merged
