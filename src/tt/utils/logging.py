"""Setup de logging do teams-transcript, baseado em loguru.

PRIVACIDADE — requisito do projeto
-----------------------------------
Este módulo expõe APENAS a configuração de sinks/formatação de log. Ele NÃO
loga nenhum conteúdo transcrito de calls. O pipeline de transcrição e resumo
não deve passar texto de fala para o logger; logs servem para diagnóstico
operacional (estado, erros, tempos), nunca para o conteúdo das reuniões.

Quem chamar ``logger.*`` em outros módulos é responsável por não incluir
trechos de transcrição nas mensagens. Mantenha logs livres de dados sensíveis.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

# Formato sem dados sensíveis: timestamp, nível, origem e a mensagem.
_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
    "{name}:{function}:{line} - {message}"
)


def configure_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Configura os sinks do loguru para a aplicação.

    PRIVACIDADE: nenhuma mensagem deve conter conteúdo transcrito de calls —
    veja o docstring do módulo. Esta função apenas prepara console e arquivo.

    Args:
        level: nível mínimo de log (``DEBUG``, ``INFO``, ``WARNING``, ...).
        log_file: caminho opcional para um arquivo de log com rotação. O
            diretório pai é criado se não existir.
    """
    logger.remove()

    logger.add(
        sys.stderr,
        level=level,
        format=_CONSOLE_FORMAT,
        colorize=True,
        backtrace=False,
        diagnose=False,  # não despeja valores de variáveis locais nos tracebacks
    )

    if log_file is not None:
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_path,
            level=level,
            format=_FILE_FORMAT,
            rotation="10 MB",
            retention="14 days",
            encoding="utf-8",
            backtrace=False,
            diagnose=False,
        )

    logger.debug("Logging configurado (level={})", level)


__all__ = ["configure_logging", "logger"]
