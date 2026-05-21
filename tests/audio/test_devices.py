"""Testes de `tt.audio.devices`.

O módulo deve importar sem `sounddevice`/`soundcard` (import preguiçoso). Os
testes de degradação ("erro claro sem backend") só fazem sentido quando a
extra `audio` NÃO está instalada — quando ela está (ambiente do MVP), esses
testes são pulados.
"""

from __future__ import annotations

import importlib

import pytest


def _skip_if_installed(module_name: str) -> None:
    """Pula o teste se a lib de backend estiver instalada."""
    try:
        importlib.import_module(module_name)
    except ImportError:
        return
    pytest.skip(f"{module_name} instalado — caminho de erro não aplicável")


def test_module_imports_without_audio_libs():
    # O ponto central da arquitetura de import preguiçoso: importar o módulo
    # NÃO pode exigir sounddevice/soundcard.
    mod = importlib.import_module("tt.audio.devices")
    assert hasattr(mod, "list_input_devices")
    assert hasattr(mod, "find_loopback_device")
    assert hasattr(mod, "find_default_mic")


def test_audio_device_dataclass_fields():
    from tt.audio.devices import AudioDevice

    dev = AudioDevice(index=3, name="Mic", channels=2)
    assert dev.index == 3
    assert dev.name == "Mic"
    assert dev.channels == 2
    assert dev.is_loopback is False  # default


def test_list_input_devices_raises_clear_error_without_backend():
    _skip_if_installed("sounddevice")
    from tt.audio.devices import AudioBackendError, list_input_devices

    with pytest.raises(AudioBackendError) as exc:
        list_input_devices()
    msg = str(exc.value)
    assert "sounddevice" in msg
    # A mensagem deve orientar como instalar.
    assert "audio" in msg


def test_find_default_mic_raises_clear_error_without_backend():
    _skip_if_installed("sounddevice")
    from tt.audio.devices import AudioBackendError, find_default_mic

    with pytest.raises(AudioBackendError) as exc:
        find_default_mic()
    assert "sounddevice" in str(exc.value)


def test_find_loopback_device_raises_clear_error_without_backend():
    _skip_if_installed("soundcard")
    from tt.audio.devices import AudioBackendError, find_loopback_device

    with pytest.raises(AudioBackendError) as exc:
        find_loopback_device()
    assert "soundcard" in str(exc.value)


def test_audio_backend_error_is_runtime_error():
    # Permite que chamadores tratem com `except RuntimeError` de forma genérica.
    from tt.audio.devices import AudioBackendError

    assert issubclass(AudioBackendError, RuntimeError)


def test_require_returns_module_when_present():
    # Sanidade do helper: para uma lib que existe (numpy), deve devolver o módulo.
    from tt.audio.devices import _require

    np_mod = _require("numpy")
    assert np_mod.__name__ == "numpy"
