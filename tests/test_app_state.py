"""Testes da máquina de estados do app (`tt.app_state`)."""

from __future__ import annotations

from tt.app_state import AppState, StateMachine


def test_starts_idle():
    assert StateMachine().state is AppState.IDLE


def test_happy_path():
    sm = StateMachine()
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


def test_rec_without_call_is_ignored():
    sm = StateMachine()
    sm.on_rec_clicked()
    assert sm.state is AppState.IDLE


def test_stop_without_recording_is_ignored():
    sm = StateMachine()
    sm.on_call_started()
    sm.on_stop_clicked()
    assert sm.state is AppState.CALL_DETECTED


def test_call_started_ignored_when_not_idle():
    sm = StateMachine()
    sm.on_call_started()
    sm.on_rec_clicked()
    sm.on_call_started()  # já gravando — ignora
    assert sm.state is AppState.RECORDING
