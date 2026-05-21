"""Entry point CLI (Typer).

Os comandos importam os subpacotes pesados de forma preguiçosa (lazy import),
dentro de cada função — assim o `--help` e os comandos leves funcionam mesmo
sem as dependências de áudio/ML instaladas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    name="tt",
    help="teams-transcript — transcrição silenciosa de calls do Teams.",
    no_args_is_help=True,
)


@app.command()
def record(
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Arquivo WAV de saída.")
    ] = Path("meeting.wav"),
) -> None:
    """Grava áudio do sistema + microfone até Ctrl+C (Fase 1)."""
    from tt.audio.capture import record_to_wav

    record_to_wav(output)


@app.command()
def transcribe(
    wav: Annotated[Path, typer.Argument(help="Arquivo WAV de entrada.")],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Markdown de saída.")
    ] = Path("meeting.md"),
) -> None:
    """Transcreve um WAV salvo para markdown (Fase 2)."""
    from tt.transcribe.pipeline import transcribe_file

    transcribe_file(wav, output)


@app.command()
def summarize(
    transcript: Annotated[Path, typer.Argument(help="Markdown de transcrição.")],
) -> None:
    """Gera resumo de um transcript via LLM (Fase 5)."""
    from tt.summary.pipeline import summarize_file

    summarize_file(transcript)


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Texto a buscar no histórico.")],
) -> None:
    """Busca em transcrições passadas via FTS5 (Fase 7)."""
    from tt.storage.search import search_meetings

    for hit in search_meetings(query):
        meeting_id = hit.get("meeting_id", "?") if isinstance(hit, dict) else hit
        snippet = hit.get("snippet", "") if isinstance(hit, dict) else ""
        typer.echo(f"{meeting_id}  {snippet}")


@app.command()
def run() -> None:
    """Inicia o app de bandeja — botão flutuante + transcrição (MVP).

    Precisa das extras de áudio, UI e transcrição:
    ``uv sync --extra audio --extra ui --extra transcribe``.
    """
    from tt.app import App

    raise SystemExit(App().run())


if __name__ == "__main__":
    app()
