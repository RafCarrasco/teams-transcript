"""Enumeração de dispositivos de áudio de entrada.

Lida com duas fontes:

- microfone — qualquer dispositivo de entrada comum, via `sounddevice`;
- loopback — o "dispositivo" que captura o som que sai pelos alto-falantes
  (o que você ouve), via WASAPI loopback. No Windows, `soundcard` expõe
  isso pela API `all_microphones(include_loopback=True)`.

IMPORTS PREGUIÇOSOS: `sounddevice` e `soundcard` são importados DENTRO das
funções, nunca no topo do módulo. Assim `import tt.audio.devices` funciona
mesmo sem o extra `audio` instalado — só quem chama uma função que precisa
da lib é que recebe um erro claro (`AudioBackendError`).
"""

from __future__ import annotations

from dataclasses import dataclass


class AudioBackendError(RuntimeError):
    """Uma lib de backend de áudio é necessária mas não está instalada/disponível."""


@dataclass(frozen=True)
class AudioDevice:
    """Descrição leve de um dispositivo de áudio.

    Estrutura simples e serializável — não guarda handles do backend, só
    o suficiente para exibir ao usuário e reabrir o dispositivo depois.
    """

    index: int | None  # índice no sounddevice; None p/ loopback do soundcard
    name: str
    channels: int
    is_loopback: bool = False


def _require(module_name: str):
    """Importa `module_name` de forma preguiçosa ou levanta `AudioBackendError`.

    Centraliza a mensagem de erro para que falta de qualquer lib de áudio
    gere uma orientação clara: como instalar o extra `audio`.
    """
    import importlib

    try:
        return importlib.import_module(module_name)
    except ImportError as exc:  # lib ausente
        raise AudioBackendError(
            f"O backend de áudio '{module_name}' não está instalado. "
            "Instale as dependências de áudio com:  uv sync --extra audio"
        ) from exc


def list_input_devices() -> list[AudioDevice]:
    """Lista os dispositivos de entrada (microfones) visíveis ao sistema.

    Usa `sounddevice.query_devices()` e filtra os que têm ao menos um canal
    de entrada. Levanta `AudioBackendError` se `sounddevice` não estiver
    instalado.
    """
    sd = _require("sounddevice")

    devices: list[AudioDevice] = []
    for index, info in enumerate(sd.query_devices()):
        # max_input_channels > 0 -> é um dispositivo de captura.
        if info.get("max_input_channels", 0) > 0:
            devices.append(
                AudioDevice(
                    index=index,
                    name=info.get("name", f"device {index}"),
                    channels=info["max_input_channels"],
                )
            )
    return devices


def find_default_mic() -> AudioDevice:
    """Devolve o microfone de entrada padrão do sistema.

    Lê o dispositivo de entrada padrão de `sounddevice.default.device` e
    resolve seus metadados. Levanta `AudioBackendError` se `sounddevice`
    não estiver instalado, e `RuntimeError` se não houver dispositivo de
    entrada padrão configurado.
    """
    sd = _require("sounddevice")

    # sd.default.device é o par (input, output); o índice 0 é a entrada.
    default_input = sd.default.device[0]
    if default_input is None or default_input < 0:
        raise RuntimeError("Nenhum microfone de entrada padrão configurado no sistema.")

    info = sd.query_devices(default_input)
    return AudioDevice(
        index=default_input,
        name=info.get("name", f"device {default_input}"),
        channels=info.get("max_input_channels", 1),
    )


def find_loopback_device() -> AudioDevice:
    """Localiza o dispositivo de loopback (som do sistema / "o que você ouve").

    Usa `soundcard`, que no Windows expõe o loopback WASAPI tratando cada
    saída como um "microfone virtual" via `all_microphones(include_loopback
    =True)`. Preferimos o loopback associado ao alto-falante padrão.

    Levanta `AudioBackendError` se `soundcard` não estiver instalado, e
    `RuntimeError` se nenhum dispositivo de loopback for encontrado (p. ex.
    em plataformas sem suporte a loopback WASAPI).
    """
    sc = _require("soundcard")

    # Todos os "microfones", incluindo os loopbacks virtuais das saídas.
    mics = sc.all_microphones(include_loopback=True)
    loopbacks = [m for m in mics if getattr(m, "isloopback", False)]
    if not loopbacks:
        raise RuntimeError(
            "Nenhum dispositivo de loopback encontrado. A captura do som do "
            "sistema requer WASAPI loopback (Windows)."
        )

    # Tenta casar o loopback com o alto-falante padrão; senão, pega o primeiro.
    chosen = loopbacks[0]
    try:
        default_speaker_name = sc.default_speaker().name
        for m in loopbacks:
            if default_speaker_name in m.name:
                chosen = m
                break
    except Exception:
        # Sem alto-falante padrão acessível — o primeiro loopback serve.
        pass

    return AudioDevice(
        index=None,  # dispositivos do soundcard são identificados por objeto, não índice
        name=chosen.name,
        channels=getattr(chosen, "channels", 2),
        is_loopback=True,
    )
