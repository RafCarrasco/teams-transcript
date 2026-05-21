"""Orquestração do app — liga Qt, tray, monitor, botão flutuante e a máquina
de estados.

Fluxo::

    CallMonitor.call_started  -> mostra o FloatingButton
    FloatingButton.rec_clicked  -> Recorder.start()
    FloatingButton.stop_clicked / call_ended  -> Recorder.stop() + transcreve
    transcrição (QThread) termina  -> Tray.notify(caminho do .txt)

A lógica testável vive em `StateMachine`, `CallMonitor`, `txt_writer` etc.;
este módulo é só fiação Qt e não tem teste automatizado (verificação manual).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from loguru import logger
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
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
    """Roda `transcribe_call` fora da thread da UI (não congela o app)."""

    done = pyqtSignal(object)   # Path do .txt gerado
    failed = pyqtSignal(str)    # mensagem de erro

    def __init__(self, wav_path, txt_path, started_at, model) -> None:
        super().__init__()
        self._wav = wav_path
        self._txt = txt_path
        self._started_at = started_at
        self._model = model

    def run(self) -> None:
        try:
            path = transcribe_call(
                self._wav, self._txt, self._started_at, model=self._model
            )
            self.done.emit(path)
        except Exception as exc:  # noqa: BLE001 - qualquer falha vai para a UI
            logger.exception("Falha na transcrição")
            self.failed.emit(str(exc))


class App:
    """O app de bandeja do MVP."""

    def __init__(self) -> None:
        self.settings = load_settings()
        self.qt = QApplication.instance() or QApplication([])
        # Fechar o botão flutuante não pode encerrar o app.
        self.qt.setQuitOnLastWindowClosed(False)

        self.sm = StateMachine()
        self.tray = Tray(self.settings.output.dir)
        self.button = FloatingButton()
        self.monitor = CallMonitor(self.settings.detection.poll_interval_seconds)

        self._recorder: Recorder | None = None
        self._started_at: datetime | None = None
        self._wav_path: Path | None = None
        self._tick: QTimer | None = None
        self._worker: _TranscribeWorker | None = None

        self._wire()

    def _wire(self) -> None:
        self.monitor.call_started.connect(self._on_call_started)
        self.monitor.call_ended.connect(self._on_call_ended)
        self.button.rec_clicked.connect(self._on_rec)
        self.button.stop_clicked.connect(self._on_stop)
        self.tray.quit_action.triggered.connect(self.qt.quit)

    def run(self) -> int:
        """Inicia o app — bloqueia no event loop do Qt até o usuário sair."""
        self.tray.show()
        self.monitor.start()
        logger.info("teams-transcript rodando — aguardando call do Teams")
        return self.qt.exec()

    # -- handlers ----------------------------------------------------------
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
        except Exception as exc:  # noqa: BLE001 - erro de áudio vai para a UI
            logger.exception("Falha ao iniciar gravação")
            self.tray.notify("Erro ao gravar", str(exc))
            self.sm.on_call_ended()  # volta o estado; aborta a gravação
            self.button.set_state("idle")
            return
        self.button.set_state("recording", elapsed="00:00")
        self._tick = QTimer()
        self._tick.timeout.connect(self._update_elapsed)
        self._tick.start(1000)

    def _update_elapsed(self) -> None:
        if self._recorder and self._recorder.is_recording:
            secs = int(self._recorder.elapsed)
            self.button.set_state(
                "recording", elapsed=f"{secs // 60:02d}:{secs % 60:02d}"
            )

    def _on_stop(self) -> None:
        self.sm.on_stop_clicked()
        if self.sm.state is AppState.TRANSCRIBING:
            self._begin_transcription()

    def _begin_transcription(self) -> None:
        if self._tick is not None:
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
        logger.info("Transcrição pronta: {}", path)

    def _on_transcription_failed(self, msg) -> None:
        self.sm.on_transcription_done()
        self.button.hide()
        self.tray.notify("Falha na transcrição", msg)
