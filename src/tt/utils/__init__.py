"""Utilidades do teams-transcript — configuração, logging e helpers de path.

Submódulos:
    config   modelos Pydantic das seções de configuração + `load_settings`
    logging  setup do loguru (`configure_logging`) — sem conteúdo transcrito
    paths    helpers de path (`expand`, `ensure_dir`, `app_data_dir`)
"""

from __future__ import annotations

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
from tt.utils.logging import configure_logging
from tt.utils.paths import app_data_dir, ensure_dir, expand

__all__ = [
    # config
    "AudioConfig",
    "TranscribeConfig",
    "DiarizationConfig",
    "SummaryConfig",
    "StorageConfig",
    "UIConfig",
    "DetectionConfig",
    "Settings",
    "load_settings",
    # logging
    "configure_logging",
    # paths
    "expand",
    "ensure_dir",
    "app_data_dir",
]
