"""Testes da lógica pura do aligner: align() e merge_consecutive().

Esta é a parte testável e crítica do módulo `transcribe` — não depende de
nenhuma lib de ML, só de aritmética de intervalos. Por isso tem cobertura
completa (TDD).
"""

from __future__ import annotations

from tt.transcribe.aligner import align, merge_consecutive

# --------------------------------------------------------------------------
# align(): atribuição de speaker por sobreposição temporal
# --------------------------------------------------------------------------


def test_align_assigns_speaker_with_largest_overlap():
    """Cada segment recebe o speaker do turno com maior sobreposição."""
    segments = [
        {"start": 0.0, "end": 5.0, "text": "Bom dia."},
        {"start": 5.0, "end": 10.0, "text": "Vamos comecar."},
    ]
    turns = [
        {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"},
    ]

    result = align(segments, turns)

    assert result[0]["speaker"] == "SPEAKER_00"
    assert result[1]["speaker"] == "SPEAKER_01"
    # Texto e tempos preservados intactos.
    assert result[0]["text"] == "Bom dia."
    assert result[0]["start"] == 0.0
    assert result[0]["end"] == 5.0


def test_align_partial_overlap_picks_dominant_speaker():
    """Com sobreposição parcial em dois turnos, ganha quem cobre mais tempo."""
    # Segment 2.0-10.0 (8s). Turno A cobre 2.0-4.0 (2s), turno B cobre 4.0-10.0 (6s).
    segments = [{"start": 2.0, "end": 10.0, "text": "Trecho dividido."}]
    turns = [
        {"start": 0.0, "end": 4.0, "speaker": "SPEAKER_00"},
        {"start": 4.0, "end": 12.0, "speaker": "SPEAKER_01"},
    ]

    result = align(segments, turns)

    assert result[0]["speaker"] == "SPEAKER_01"


def test_align_segment_with_no_matching_turn_is_unknown():
    """Segment sem qualquer sobreposição recebe speaker UNKNOWN."""
    segments = [{"start": 100.0, "end": 105.0, "text": "Fora de qualquer turno."}]
    turns = [
        {"start": 0.0, "end": 10.0, "speaker": "SPEAKER_00"},
    ]

    result = align(segments, turns)

    assert result[0]["speaker"] == "UNKNOWN"


def test_align_empty_turns_returns_segments_without_speaker():
    """Sem turnos de diarização, os segments saem sem chave 'speaker' (sem crash)."""
    segments = [
        {"start": 0.0, "end": 5.0, "text": "Sem diarizacao."},
        {"start": 5.0, "end": 9.0, "text": "Segundo trecho."},
    ]

    result = align(segments, [])

    assert len(result) == 2
    assert "speaker" not in result[0]
    assert "speaker" not in result[1]
    assert result[0]["text"] == "Sem diarizacao."


def test_align_empty_segments_returns_empty_list():
    """Sem segments de texto, o resultado é uma lista vazia."""
    turns = [{"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"}]

    assert align([], turns) == []


def test_align_does_not_mutate_input_segments():
    """align() não deve mutar os dicts originais (retorna cópias)."""
    segments = [{"start": 0.0, "end": 5.0, "text": "Original."}]
    turns = [{"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"}]

    align(segments, turns)

    assert "speaker" not in segments[0]


def test_align_touching_intervals_do_not_count_as_overlap():
    """Intervalos que apenas se tocam (fim==inicio) têm sobreposição zero."""
    # Segment 5.0-10.0 toca o turno A em 5.0 mas só sobrepõe o turno B.
    segments = [{"start": 5.0, "end": 10.0, "text": "Toca a borda."}]
    turns = [
        {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"},
    ]

    result = align(segments, turns)

    assert result[0]["speaker"] == "SPEAKER_01"


def test_align_multiple_turns_same_speaker_sum_overlap():
    """Vários turnos do mesmo speaker somam sobreposição antes de comparar."""
    # Segment 0-10. SPEAKER_00 aparece em dois turnos curtos (2+2=4s),
    # SPEAKER_01 num turno só de 3s. Mesmo fragmentado, SPEAKER_00 ganha.
    segments = [{"start": 0.0, "end": 10.0, "text": "Trecho longo."}]
    turns = [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
        {"start": 2.0, "end": 5.0, "speaker": "SPEAKER_01"},
        {"start": 5.0, "end": 7.0, "speaker": "SPEAKER_00"},
    ]

    result = align(segments, turns)

    assert result[0]["speaker"] == "SPEAKER_00"


# --------------------------------------------------------------------------
# merge_consecutive(): fusão de segments adjacentes do mesmo speaker
# --------------------------------------------------------------------------


def test_merge_consecutive_merges_same_speaker():
    """Segments adjacentes do mesmo speaker viram um só."""
    segments = [
        {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00", "text": "Bom dia."},
        {"start": 3.0, "end": 6.0, "speaker": "SPEAKER_00", "text": "Tudo bem?"},
    ]

    result = merge_consecutive(segments)

    assert len(result) == 1
    assert result[0]["speaker"] == "SPEAKER_00"
    assert result[0]["start"] == 0.0
    assert result[0]["end"] == 6.0
    assert result[0]["text"] == "Bom dia. Tudo bem?"


def test_merge_consecutive_keeps_speaker_change():
    """Troca de speaker quebra a fusão — segments distintos permanecem."""
    segments = [
        {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00", "text": "Oi."},
        {"start": 3.0, "end": 6.0, "speaker": "SPEAKER_01", "text": "Ola."},
        {"start": 6.0, "end": 9.0, "speaker": "SPEAKER_01", "text": "Tudo certo."},
    ]

    result = merge_consecutive(segments)

    assert len(result) == 2
    assert result[0]["speaker"] == "SPEAKER_00"
    assert result[0]["text"] == "Oi."
    assert result[1]["speaker"] == "SPEAKER_01"
    assert result[1]["text"] == "Ola. Tudo certo."
    assert result[1]["start"] == 3.0
    assert result[1]["end"] == 9.0


def test_merge_consecutive_empty_list():
    """Lista vazia entra, lista vazia sai."""
    assert merge_consecutive([]) == []


def test_merge_consecutive_single_segment():
    """Um único segment é retornado como está (uma cópia)."""
    segments = [{"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00", "text": "So um."}]

    result = merge_consecutive(segments)

    assert len(result) == 1
    assert result[0]["text"] == "So um."


def test_merge_consecutive_without_speaker_key_merges_all():
    """Sem chave 'speaker' (diarização desligada), tudo é tratado como mesmo falante."""
    segments = [
        {"start": 0.0, "end": 3.0, "text": "Primeiro."},
        {"start": 3.0, "end": 6.0, "text": "Segundo."},
    ]

    result = merge_consecutive(segments)

    assert len(result) == 1
    assert result[0]["text"] == "Primeiro. Segundo."
    assert result[0]["start"] == 0.0
    assert result[0]["end"] == 6.0


def test_merge_consecutive_does_not_mutate_input():
    """merge_consecutive() não deve mutar os dicts de entrada."""
    segments = [
        {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00", "text": "A."},
        {"start": 3.0, "end": 6.0, "speaker": "SPEAKER_00", "text": "B."},
    ]

    merge_consecutive(segments)

    assert segments[0]["text"] == "A."
    assert segments[0]["end"] == 3.0


def test_merge_consecutive_strips_and_joins_text_cleanly():
    """Texto dos segments é unido com espaço único, sem espaços duplicados."""
    segments = [
        {"start": 0.0, "end": 3.0, "speaker": "S0", "text": "  Com espacos  "},
        {"start": 3.0, "end": 6.0, "speaker": "S0", "text": " extras "},
    ]

    result = merge_consecutive(segments)

    assert result[0]["text"] == "Com espacos extras"
