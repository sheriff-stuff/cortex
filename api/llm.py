"""Ollama HTTP client and transcript chunking logic."""

import json
from typing import Callable

import requests

from api.config import Config
from api.transcribe import Segment


def check_ollama(config: Config) -> bool:
    """Check if Ollama is running and responsive."""
    try:
        resp = requests.get(f"{config.ollama_url}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def check_model_available(config: Config) -> bool:
    """Check if the configured model is pulled in Ollama."""
    try:
        resp = requests.get(f"{config.ollama_url}/api/tags", timeout=5)
        if resp.status_code != 200:
            return False
        models = resp.json().get("models", [])
        model_name = config.llm_model
        return any(
            m.get("name", "").startswith(model_name)
            for m in models
        )
    except (requests.ConnectionError, json.JSONDecodeError):
        return False


def query_ollama(prompt: str, config: Config) -> str:
    """Send a prompt to Ollama and return the response text."""
    resp = requests.post(
        f"{config.ollama_url}/api/generate",
        json={
            "model": config.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 4096,
            },
        },
        timeout=600,  # LLM can take a while
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: words * 1.3."""
    return int(len(text.split()) * 1.3)


def chunk_transcript(
    segments: list[Segment],
    config: Config,
) -> list[list[Segment]]:
    """Split segments into chunks respecting token limits with time-based overlap.

    Each chunk stays under chunk_max_tokens. Adjacent chunks overlap by
    chunk_overlap_seconds to capture Q&A pairs spanning boundaries.
    """
    if not segments:
        return []

    max_tokens = config.chunk_max_tokens
    overlap_seconds = config.chunk_overlap_seconds

    chunks: list[list[Segment]] = []
    current_chunk: list[Segment] = []
    current_tokens = 0

    for seg in segments:
        seg_tokens = _estimate_tokens(seg.text)

        if current_tokens + seg_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk)

            # Start new chunk with overlap from previous
            overlap_start_time = current_chunk[-1].end - overlap_seconds
            current_chunk = [
                s for s in current_chunk
                if s.start >= overlap_start_time
            ]
            current_tokens = sum(_estimate_tokens(s.text) for s in current_chunk)

        current_chunk.append(seg)
        current_tokens += seg_tokens

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
