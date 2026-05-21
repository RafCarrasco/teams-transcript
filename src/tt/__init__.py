"""teams-transcript — transcrição silenciosa de calls do Microsoft Teams.

Pacote raiz. Subpacotes:
    audio       captura WASAPI loopback + microfone
    transcribe  Whisper + diarização + alinhamento
    summary     geração de resumo via LLM (Gemini, free tier)
    storage     SQLite + FTS5 + CRUD de meetings
    ui          system tray + janela flutuante (PyQt6)
    detection   monitoramento de processo do Teams
    utils       config, logging, helpers
"""

__version__ = "0.1.0"
