"""CLI entry point using Click."""

from pathlib import Path

import click
from rich.console import Console

from api import __version__
from api.config import load_config

console = Console()

SUPPORTED_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac",  # audio
    ".mp4", ".mkv", ".avi", ".mov",  # video
}


@click.group()
@click.version_option(version=__version__, prog_name="meeting-notes")
def main():
    """Local AI meeting notes processor."""


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "-o", "--output-dir",
    type=click.Path(),
    default=None,
    help="Output directory (default: ./meeting-notes)",
)
@click.option("--whisper-model", default=None, help="Whisper model name (default: large-v3)")
@click.option("--llm-provider", default=None, type=click.Choice(["ollama", "openai"]), help="LLM provider (default: ollama)")
@click.option("--llm-model", default=None, help="LLM model name (default: qwen2.5-coder:32b)")
@click.option("--llm-api-key", default=None, help="API key for external LLM provider")
@click.option("--llm-base-url", default=None, help="Base URL for OpenAI-compatible API")
@click.option("--ollama-url", default=None, help="Ollama API URL")
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Config file path")
@click.option("--no-llm", is_flag=True, default=False, help="Skip LLM extraction, output transcript only")
@click.option("--hf-token", default=None, help="HuggingFace token for pyannote diarization model")
def process(file, output_dir, whisper_model, llm_provider, llm_model, llm_api_key, llm_base_url, ollama_url, config_path, no_llm, hf_token):
    """Process a meeting recording into structured notes."""
    file_path = Path(file)

    # Validate file extension
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise click.BadParameter(
            f"Unsupported format '{file_path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            param_hint="'FILE'",
        )

    # Build config
    cli_overrides = {
        "whisper_model": whisper_model,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "llm_api_key": llm_api_key,
        "llm_base_url": llm_base_url,
        "ollama_url": ollama_url,
        "hf_token": hf_token,
    }
    if output_dir is not None:
        cli_overrides["default_output_dir"] = output_dir

    config = load_config(
        config_path=Path(config_path) if config_path else None,
        cli_overrides=cli_overrides,
    )

    # Import here to avoid slow imports on --help
    from api.pipeline import process_meeting

    try:
        output_path = process_meeting(file_path, config, no_llm=no_llm)
        console.print(f"\n[bold green]Done![/] Notes saved to: {output_path}")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/] {e}")
        raise SystemExit(1)


def _register_serve():
    """Lazy-import serve command to avoid pulling in FastAPI for CLI users."""
    try:
        from api.server import serve
        main.add_command(serve)
    except ImportError:
        pass


_register_serve()
