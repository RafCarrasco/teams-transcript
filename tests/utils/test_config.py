"""Testes dos modelos de configuração e do carregamento (`tt.utils.config`)."""

from __future__ import annotations

import textwrap

import pytest
from pydantic import ValidationError

from tt.utils.config import (
    AudioConfig,
    DetectionConfig,
    DiarizationConfig,
    Settings,
    StorageConfig,
    SummaryConfig,
    TranscribeConfig,
    UIConfig,
    load_settings,
)

# YAML completo, espelha settings.example.yaml.
FULL_YAML = textwrap.dedent(
    """
    audio:
      sample_rate: 16000
      channels: mono
      loopback_enabled: true
      mic_enabled: true
      chunk_seconds: 30

    transcribe:
      model: medium
      compute_type: int8
      device: auto
      language: auto
      vad_enabled: true

    diarization:
      enabled: true
      user_baseline_path: ~/.config/teams-transcript/voice_baseline.wav
      max_speakers: 6
      huggingface_token: ${HF_TOKEN}

    summary:
      enabled: true
      provider: google
      model: gemini-2.5-flash
      api_key: ${GEMINI_API_KEY}
      language: pt
      enable_caching: false

    storage:
      data_dir: ~/.local/share/teams-transcript
      db_path: ~/.local/share/teams-transcript/meetings.db
      keep_audio: false
      retention_days: 365

    ui:
      hotkey: ctrl+shift+t
      show_floating_window: false
      notify_on_complete: true

    detection:
      auto_detect_teams: true
      poll_interval_seconds: 5
    """
)


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# --------------------------------------------------------------------------
# load_settings — caminho feliz
# --------------------------------------------------------------------------
def test_load_settings_reads_full_yaml(tmp_path, monkeypatch):
    """Um YAML completo deve popular todas as seções."""
    monkeypatch.setenv("HF_TOKEN", "hf_abc")
    monkeypatch.setenv("GEMINI_API_KEY", "gem_xyz")
    path = _write(tmp_path, "settings.yaml", FULL_YAML)

    s = load_settings(path)

    assert isinstance(s, Settings)
    assert s.audio.sample_rate == 16000
    assert s.audio.channels == "mono"
    assert s.transcribe.model == "medium"
    assert s.diarization.max_speakers == 6
    assert s.summary.provider == "google"
    assert s.summary.model == "gemini-2.5-flash"
    assert s.storage.retention_days == 365
    assert s.ui.hotkey == "ctrl+shift+t"
    assert s.detection.poll_interval_seconds == 5


# --------------------------------------------------------------------------
# expansão de ${VAR}
# --------------------------------------------------------------------------
def test_env_var_expanded_when_set(tmp_path, monkeypatch):
    """`${VAR}` é substituído pelo valor da variável de ambiente."""
    monkeypatch.setenv("HF_TOKEN", "hf_token_real")
    monkeypatch.setenv("GEMINI_API_KEY", "gem_key_real")
    path = _write(tmp_path, "settings.yaml", FULL_YAML)

    s = load_settings(path)

    assert s.diarization.huggingface_token == "hf_token_real"
    assert s.summary.api_key == "gem_key_real"


def test_env_var_missing_becomes_empty_string(tmp_path, monkeypatch):
    """`${VAR}` sem valor no ambiente vira string vazia, sem quebrar."""
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    path = _write(tmp_path, "settings.yaml", FULL_YAML)

    s = load_settings(path)

    assert s.diarization.huggingface_token == ""
    assert s.summary.api_key == ""


def test_env_var_missing_logs_warning(tmp_path, monkeypatch, caplog):
    """Variável ausente deve registrar um warning."""
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    path = _write(tmp_path, "settings.yaml", FULL_YAML)

    import logging as _stdlib_logging

    from tt.utils import config as config_mod

    # loguru -> propaga para o logging stdlib captado pelo caplog.
    handler_id = config_mod.logger.add(
        caplog.handler, level="WARNING", format="{message}"
    )
    try:
        with caplog.at_level(_stdlib_logging.WARNING):
            load_settings(path)
    finally:
        config_mod.logger.remove(handler_id)

    assert any("HF_TOKEN" in m for m in caplog.messages)


# --------------------------------------------------------------------------
# defaults
# --------------------------------------------------------------------------
def test_defaults_applied_when_section_missing(tmp_path):
    """Seções ausentes no YAML usam os defaults dos modelos."""
    minimal = "audio:\n  sample_rate: 16000\n"
    path = _write(tmp_path, "settings.yaml", minimal)

    s = load_settings(path)

    # seções ausentes existem, com o tipo certo e os defaults
    assert isinstance(s.transcribe, TranscribeConfig)
    assert isinstance(s.diarization, DiarizationConfig)
    assert isinstance(s.summary, SummaryConfig)
    assert isinstance(s.storage, StorageConfig)
    assert isinstance(s.ui, UIConfig)
    assert isinstance(s.detection, DetectionConfig)
    assert s.transcribe.model == "medium"
    assert s.summary.provider == "google"
    assert s.storage.retention_days == 365
    assert s.ui.hotkey == "ctrl+shift+t"
    assert s.detection.auto_detect_teams is True


def test_defaults_match_example_for_empty_yaml(tmp_path):
    """YAML vazio produz um Settings totalmente default."""
    path = _write(tmp_path, "settings.yaml", "")
    s = load_settings(path)
    assert isinstance(s, Settings)
    assert s.audio.sample_rate == 16000


# --------------------------------------------------------------------------
# validações
# --------------------------------------------------------------------------
def test_invalid_provider_rejected():
    """`summary.provider` fora do conjunto permitido é rejeitado."""
    with pytest.raises(ValidationError):
        SummaryConfig(provider="invalido")


def test_valid_providers_accepted():
    """google / anthropic / openai são aceitos."""
    for prov in ("google", "anthropic", "openai"):
        cfg = SummaryConfig(provider=prov, model="x")
        assert cfg.provider == prov


def test_empty_model_rejected():
    """`summary.model` não pode ser vazio."""
    with pytest.raises(ValidationError):
        SummaryConfig(model="")


def test_non_positive_sample_rate_rejected():
    """`audio.sample_rate` <= 0 é rejeitado."""
    with pytest.raises(ValidationError):
        AudioConfig(sample_rate=0)
    with pytest.raises(ValidationError):
        AudioConfig(sample_rate=-1)


def test_invalid_provider_via_load_settings(tmp_path):
    """provider inválido vindo do YAML também quebra."""
    bad = "summary:\n  provider: foobar\n"
    path = _write(tmp_path, "settings.yaml", bad)
    with pytest.raises(ValidationError):
        load_settings(path)


# --------------------------------------------------------------------------
# expansão de ~ em paths
# --------------------------------------------------------------------------
def test_tilde_paths_expanded(tmp_path, monkeypatch):
    """Paths com `~` nos modelos devem ser expandidos para absoluto."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    path = _write(tmp_path, "settings.yaml", FULL_YAML)

    s = load_settings(path)

    assert "~" not in str(s.storage.data_dir)
    assert s.storage.data_dir.is_absolute()
    assert "~" not in str(s.diarization.user_baseline_path)
    assert s.diarization.user_baseline_path.is_absolute()


# --------------------------------------------------------------------------
# resolução do path padrão
# --------------------------------------------------------------------------
def test_load_settings_prefers_settings_yaml(tmp_path, monkeypatch):
    """Sem path explícito, prefere settings.yaml na raiz."""
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "settings.yaml", "audio:\n  sample_rate: 22050\n")
    _write(tmp_path, "settings.example.yaml", "audio:\n  sample_rate: 16000\n")

    s = load_settings()

    assert s.audio.sample_rate == 22050


def test_load_settings_falls_back_to_example(tmp_path, monkeypatch):
    """Sem settings.yaml, cai para settings.example.yaml."""
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "settings.example.yaml", "audio:\n  sample_rate: 48000\n")

    s = load_settings()

    assert s.audio.sample_rate == 48000


def test_load_settings_missing_file_raises(tmp_path):
    """Path explícito inexistente levanta erro."""
    with pytest.raises(FileNotFoundError):
        load_settings(tmp_path / "nao_existe.yaml")
