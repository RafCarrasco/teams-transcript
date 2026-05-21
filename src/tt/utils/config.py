"""Modelos de configuração e carregamento (`settings.yaml`).

Cada seção do ``settings.yaml`` vira um modelo Pydantic v2 com defaults que
batem com o ``settings.example.yaml``. :class:`Settings` agrega todos.

:func:`load_settings` lê o YAML, expande referências ``${VAR}`` a partir do
ambiente (carregando ``.env`` se existir) e valida tudo via Pydantic.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Padrão de referência a variável de ambiente: ${NOME_DA_VAR}
_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

# Provedores de LLM suportados para o resumo.
Provider = Literal["google", "anthropic", "openai"]


# --------------------------------------------------------------------------
# Modelos por seção
# --------------------------------------------------------------------------
class _Section(BaseModel):
    """Base comum: rejeita chaves desconhecidas para pegar typos no YAML."""

    model_config = ConfigDict(extra="forbid")


class AudioConfig(_Section):
    """Seção ``audio`` — captura de áudio."""

    sample_rate: int = 16000
    channels: Literal["mono", "stereo"] = "mono"
    loopback_enabled: bool = True
    mic_enabled: bool = True
    chunk_seconds: int = 30

    @field_validator("sample_rate")
    @classmethod
    def _sample_rate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("sample_rate deve ser positivo")
        return v

    @field_validator("chunk_seconds")
    @classmethod
    def _chunk_seconds_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("chunk_seconds deve ser positivo")
        return v


class TranscribeConfig(_Section):
    """Seção ``transcribe`` — Whisper e VAD."""

    model: Literal["tiny", "base", "small", "medium", "large-v3"] = "medium"
    compute_type: Literal["int8", "int8_float16", "float16"] = "int8"
    device: Literal["auto", "cpu", "cuda"] = "auto"
    language: str = "auto"
    vad_enabled: bool = True


class DiarizationConfig(_Section):
    """Seção ``diarization`` — separação de falantes (pyannote)."""

    enabled: bool = True
    user_baseline_path: Path = Path("~/.config/teams-transcript/voice_baseline.wav")
    max_speakers: int = 6
    huggingface_token: str = ""

    @field_validator("max_speakers")
    @classmethod
    def _max_speakers_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_speakers deve ser positivo")
        return v

    @field_validator("user_baseline_path")
    @classmethod
    def _expand_baseline(cls, v: Path) -> Path:
        return v.expanduser()


class SummaryConfig(_Section):
    """Seção ``summary`` — geração de resumo via LLM."""

    enabled: bool = True
    provider: Provider = "google"
    model: str = "gemini-2.5-flash"
    api_key: str = ""
    language: str = "pt"
    enable_caching: bool = False

    @field_validator("model")
    @classmethod
    def _model_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("summary.model não pode ser vazio")
        return v


class StorageConfig(_Section):
    """Seção ``storage`` — diretório de dados e banco SQLite."""

    data_dir: Path = Path("~/.local/share/teams-transcript")
    db_path: Path = Path("~/.local/share/teams-transcript/meetings.db")
    keep_audio: bool = False
    retention_days: int = 365

    @field_validator("retention_days")
    @classmethod
    def _retention_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("retention_days não pode ser negativo (0 = guardar sempre)")
        return v

    @field_validator("data_dir", "db_path")
    @classmethod
    def _expand_paths(cls, v: Path) -> Path:
        return v.expanduser()


class UIConfig(_Section):
    """Seção ``ui`` — atalho global e janela flutuante."""

    hotkey: str = "ctrl+shift+t"
    show_floating_window: bool = False
    notify_on_complete: bool = True


class DetectionConfig(_Section):
    """Seção ``detection`` — monitoramento de calls do Teams."""

    auto_detect_teams: bool = True
    poll_interval_seconds: int = 5

    @field_validator("poll_interval_seconds")
    @classmethod
    def _poll_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("poll_interval_seconds deve ser positivo")
        return v


class Settings(BaseModel):
    """Configuração raiz — agrega todas as seções.

    Seções ausentes no YAML usam os defaults dos respectivos modelos.
    """

    model_config = ConfigDict(extra="forbid")

    audio: AudioConfig = Field(default_factory=AudioConfig)
    transcribe: TranscribeConfig = Field(default_factory=TranscribeConfig)
    diarization: DiarizationConfig = Field(default_factory=DiarizationConfig)
    summary: SummaryConfig = Field(default_factory=SummaryConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)


# --------------------------------------------------------------------------
# Carregamento
# --------------------------------------------------------------------------
def _project_root() -> Path:
    """Raiz do projeto — diretório de trabalho atual.

    `load_settings` procura ``settings.yaml`` aqui quando nenhum path é dado.
    """
    return Path.cwd()


def _resolve_path(path: Path | None) -> Path:
    """Resolve qual arquivo de configuração carregar.

    - `path` explícito: usa esse (erro se não existir).
    - `None`: ``settings.yaml`` na raiz; senão ``settings.example.yaml``.
    """
    if path is not None:
        p = Path(path).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {p}")
        return p

    root = _project_root()
    primary = root / "settings.yaml"
    if primary.is_file():
        return primary

    example = root / "settings.example.yaml"
    if example.is_file():
        logger.warning(
            "settings.yaml não encontrado — usando settings.example.yaml como fallback"
        )
        return example

    raise FileNotFoundError(
        f"Nenhum settings.yaml ou settings.example.yaml encontrado em {root}"
    )


def _load_dotenv() -> None:
    """Carrega o ``.env`` da raiz no ambiente, se existir.

    Não sobrescreve variáveis já definidas no ambiente do processo.
    """
    env_path = _project_root() / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:  # pragma: no cover - dotenv é dep transitiva instalada
        logger.warning("python-dotenv indisponível — .env não foi carregado")


def _expand_env(value: Any) -> Any:
    """Expande recursivamente referências ``${VAR}`` numa árvore YAML.

    Variáveis sem valor no ambiente viram string vazia e geram um warning,
    para não quebrar o carregamento.
    """
    if isinstance(value, str):

        def _sub(match: re.Match[str]) -> str:
            name = match.group(1)
            env_val = os.environ.get(name)
            if env_val is None:
                logger.warning(
                    "Variável de ambiente '{}' não definida — usando string vazia",
                    name,
                )
                return ""
            return env_val

        return _ENV_REF.sub(_sub, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_settings(path: Path | None = None) -> Settings:
    """Carrega, expande variáveis de ambiente e valida a configuração.

    Args:
        path: arquivo de configuração explícito. Se ``None``, procura
            ``settings.yaml`` na raiz do projeto e cai para
            ``settings.example.yaml``.

    Returns:
        Uma instância validada de :class:`Settings`.

    Raises:
        FileNotFoundError: se nenhum arquivo de configuração for encontrado.
        pydantic.ValidationError: se a configuração for inválida.
    """
    _load_dotenv()

    config_path = _resolve_path(path)
    logger.debug("Carregando configuração de {}", config_path)

    raw_text = config_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text) or {}
    if not isinstance(data, dict):
        raise ValueError(
            f"Configuração inválida em {config_path}: raiz deve ser um mapeamento"
        )

    expanded = _expand_env(data)
    return Settings.model_validate(expanded)


__all__ = [
    "AudioConfig",
    "TranscribeConfig",
    "DiarizationConfig",
    "SummaryConfig",
    "StorageConfig",
    "UIConfig",
    "DetectionConfig",
    "Settings",
    "load_settings",
    "logger",
]
