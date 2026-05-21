"""Testes do setup de logging (`tt.utils.logging`)."""

from __future__ import annotations

from tt.utils.logging import configure_logging


def test_configure_logging_returns_without_error():
    """`configure_logging` deve rodar sem exceção com defaults."""
    configure_logging()


def test_configure_logging_creates_log_file(tmp_path):
    """Quando `log_file` é dado, o arquivo (e diretório pai) é criado."""
    log_file = tmp_path / "logs" / "app.log"

    configure_logging(level="DEBUG", log_file=log_file)

    from loguru import logger

    logger.info("linha de teste")

    # loguru cria o sink lazily; o diretório pai deve existir já.
    assert log_file.parent.is_dir()
    assert log_file.exists()


def test_configure_logging_accepts_level_string(tmp_path):
    """Aceita string de nível arbitrária válida."""
    configure_logging(level="WARNING")


def test_logging_module_has_privacy_docstring():
    """O módulo documenta a restrição de privacidade (sem conteúdo transcrito)."""
    import tt.utils.logging as logging_mod

    doc = (logging_mod.__doc__ or "") + (configure_logging.__doc__ or "")
    lowered = doc.lower()
    assert "privacidade" in lowered or "privacy" in lowered
