"""Run the meeting-notes API server."""

import warnings
from pathlib import Path

import click

# Suppress harmless torchcodec/pyannote warnings on Windows
# (pyannote falls back to ffmpeg for audio loading)
warnings.filterwarnings("ignore", message="torchcodec is not installed correctly")
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote.audio.utils.reproducibility")


@click.command()
@click.option("--host", default="127.0.0.1", help="Bind host")
@click.option("--port", default=9000, type=int, help="Bind port")
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Config file path")
@click.option("--database-url", default=None, help="Database connection string (default: sqlite:///meeting-notes.db)")
@click.option("--reload", is_flag=True, default=False, help="Auto-reload on code changes (dev mode)")
def serve(host, port, config_path, database_url, reload):
    """Start the meeting-notes API server."""
    import os
    import uvicorn

    from api.api import create_app
    from api.config import load_config

    # CLI flag takes priority, then env var
    if database_url is None:
        database_url = os.environ.get("MEETING_NOTES_DATABASE_URL")

    cli_overrides = {}
    if database_url is not None:
        cli_overrides["database_url"] = database_url

    if reload:
        # uvicorn --reload requires a factory string, not an app instance
        import os

        if config_path:
            os.environ["MEETING_NOTES_CONFIG"] = str(config_path)
        if database_url:
            os.environ["MEETING_NOTES_DATABASE_URL"] = database_url
        uvicorn.run(
            "api.api:create_app_from_env",
            factory=True,
            host=host,
            port=port,
            reload=True,
            reload_dirs=["api"],
        )
    else:
        config = load_config(
            config_path=Path(config_path) if config_path else None,
            cli_overrides=cli_overrides,
        )
        app = create_app(config)
        uvicorn.run(app, host=host, port=port)
