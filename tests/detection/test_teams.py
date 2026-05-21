"""Testes da detecção de processo do Teams — `psutil.process_iter` mockado."""

from __future__ import annotations

import psutil

from tt.detection import teams


class FakeProcess:
    """Stub mínimo de `psutil.Process` para os testes.

    Replica o atributo `info` (dict) que `process_iter(["name"])` popula.
    Se `raises` for setado, ler `info` levanta a exceção — simula o processo
    que morre durante a varredura.
    """

    def __init__(self, name, raises=None):
        self._raises = raises
        self._name = name

    @property
    def info(self):
        if self._raises is not None:
            raise self._raises
        return {"name": self._name}


def _fake_process_iter(processes):
    """Devolve uma função que substitui `psutil.process_iter`."""

    def _iter(attrs=None):  # assinatura compatível com process_iter
        return iter(processes)

    return _iter


def test_is_teams_running_true_for_classic_teams(monkeypatch):
    procs = [FakeProcess("chrome.exe"), FakeProcess("Teams.exe")]
    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter(procs))
    assert teams.is_teams_running() is True


def test_is_teams_running_true_for_new_teams(monkeypatch):
    # Novo Teams (WebView2): ms-teams.exe.
    procs = [FakeProcess("ms-teams.exe"), FakeProcess("explorer.exe")]
    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter(procs))
    assert teams.is_teams_running() is True


def test_is_teams_running_false_when_absent(monkeypatch):
    procs = [FakeProcess("chrome.exe"), FakeProcess("explorer.exe")]
    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter(procs))
    assert teams.is_teams_running() is False


def test_is_teams_running_false_for_empty_process_list(monkeypatch):
    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter([]))
    assert teams.is_teams_running() is False


def test_detection_is_case_insensitive(monkeypatch):
    # Variações de capitalização do nome devem ser detectadas.
    for name in ("teams.exe", "TEAMS.EXE", "Teams.Exe", "MS-Teams.exe"):
        procs = [FakeProcess(name)]
        monkeypatch.setattr(psutil, "process_iter", _fake_process_iter(procs))
        assert teams.is_teams_running() is True, name


def test_teams_processes_returns_only_matching(monkeypatch):
    procs = [
        FakeProcess("chrome.exe"),
        FakeProcess("Teams.exe"),
        FakeProcess("ms-teams.exe"),
        FakeProcess("notepad.exe"),
    ]
    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter(procs))
    result = teams.teams_processes()
    assert len(result) == 2
    names = {p.info["name"] for p in result}
    assert names == {"Teams.exe", "ms-teams.exe"}


def test_teams_processes_empty_when_no_teams(monkeypatch):
    procs = [FakeProcess("chrome.exe")]
    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter(procs))
    assert teams.teams_processes() == []


def test_dead_process_is_skipped(monkeypatch):
    # Um processo que morre durante a varredura não deve quebrar a detecção.
    procs = [
        FakeProcess(None, raises=psutil.NoSuchProcess(pid=1)),
        FakeProcess("Teams.exe"),
    ]
    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter(procs))
    assert teams.is_teams_running() is True


def test_access_denied_process_is_skipped(monkeypatch):
    procs = [
        FakeProcess(None, raises=psutil.AccessDenied(pid=1)),
        FakeProcess("chrome.exe"),
    ]
    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter(procs))
    assert teams.is_teams_running() is False


def test_process_with_none_name_is_ignored(monkeypatch):
    # process_iter pode entregar info["name"] == None — não deve dar erro.
    procs = [FakeProcess(None), FakeProcess("Teams.exe")]
    monkeypatch.setattr(psutil, "process_iter", _fake_process_iter(procs))
    assert teams.is_teams_running() is True
