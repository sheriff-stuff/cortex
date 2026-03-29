"""Configuration loading: defaults < YAML file < CLI flags."""

from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "meeting-notes" / "config.yaml"


@dataclass
class Config:
    whisper_model: str = "large-v3"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"
    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5-coder:32b"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    ollama_url: str = "http://localhost:11434"
    default_output_dir: str = "./meeting-notes"
    chunk_max_tokens: int = 3000
    chunk_overlap_seconds: float = 120.0
    hf_token: str = ""
    database_url: str = "sqlite:///meeting-notes.db"


def load_config(
    config_path: Path | None = None,
    cli_overrides: dict | None = None,
) -> Config:
    """Load config with priority: defaults < YAML file < CLI overrides."""
    config = Config()
    valid_fields = {fld.name for fld in fields(Config)}

    # Load YAML config file
    yaml_path = config_path or DEFAULT_CONFIG_PATH
    if yaml_path.exists():
        with open(yaml_path) as f:
            yaml_data = yaml.safe_load(f) or {}
        for key, value in yaml_data.items():
            if key in valid_fields and value is not None:
                setattr(config, key, value)

    # Apply CLI overrides (non-None values win)
    if cli_overrides:
        for key, value in cli_overrides.items():
            if key in valid_fields and value is not None:
                setattr(config, key, value)

    return config
