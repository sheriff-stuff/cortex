"""LLM HTTP client (Ollama + OpenAI-compatible) and transcript chunking logic."""

import json

import httpx

from api.config import Config
from api.transcribe import Segment

_SUPPORTED_PROVIDERS = ("ollama", "openai")

_client = httpx.Client()


def check_ollama(config: Config) -> bool:
    """Check if Ollama is running and responsive."""
    try:
        resp = _client.get(f"{config.ollama_url}/api/tags", timeout=5)
        return resp.status_code == 200
    except httpx.RequestError:
        return False


def check_model_available(config: Config) -> bool:
    """Check if the configured model is pulled in Ollama."""
    try:
        resp = _client.get(f"{config.ollama_url}/api/tags", timeout=5)
        if resp.status_code != 200:
            return False
        models = resp.json().get("models", [])
        model_name = config.llm_model
        return any(
            m.get("name", "").startswith(model_name)
            for m in models
        )
    except (httpx.RequestError, json.JSONDecodeError):
        return False


def query_ollama(prompt: str, config: Config) -> str:
    """Send a prompt to Ollama and return the response text."""
    resp = _client.post(
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


# --- OpenAI-compatible provider ---


def _openai_headers(config: Config) -> dict:
    """Build HTTP headers for OpenAI-compatible APIs."""
    headers = {"Content-Type": "application/json"}
    if config.llm_api_key:
        headers["Authorization"] = f"Bearer {config.llm_api_key}"
    return headers


def check_openai(config: Config) -> bool:
    """Check if an OpenAI-compatible API is reachable."""
    try:
        resp = _client.get(
            f"{config.llm_base_url}/models",
            headers=_openai_headers(config),
            timeout=10,
        )
        # 200 = OK, 404/405 = endpoint not implemented but server is up
        return resp.status_code in (200, 404, 405)
    except httpx.RequestError:
        return False


def check_openai_model_available(config: Config) -> bool:
    """Check if the configured model exists on an OpenAI-compatible API.

    Many servers (Azure, vLLM) don't implement GET /models, so 404/405
    is treated as "assume available".
    """
    try:
        resp = _client.get(
            f"{config.llm_base_url}/models",
            headers=_openai_headers(config),
            timeout=10,
        )
        if resp.status_code in (404, 405):
            return True
        if resp.status_code != 200:
            return False
        models = resp.json().get("data", [])
        return any(m.get("id") == config.llm_model for m in models)
    except (httpx.RequestError, json.JSONDecodeError):
        return False


def query_openai(prompt: str, config: Config) -> str:
    """Send a prompt to an OpenAI-compatible chat completions endpoint."""
    resp = _client.post(
        f"{config.llm_base_url}/chat/completions",
        headers=_openai_headers(config),
        json={
            "model": config.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 4096,
        },
        timeout=600,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            f"Unexpected response format from {config.llm_base_url}: {str(data)[:500]}"
        ) from exc


# --- Provider dispatchers ---


def _validate_provider(config: Config) -> str:
    """Validate and return the configured LLM provider."""
    provider = config.llm_provider
    if provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported llm_provider '{provider}'. "
            f"Supported: {', '.join(_SUPPORTED_PROVIDERS)}"
        )
    return provider


def check_llm(config: Config) -> bool:
    """Check if the configured LLM provider is reachable."""
    if _validate_provider(config) == "openai":
        return check_openai(config)
    return check_ollama(config)


def check_llm_model_available(config: Config) -> bool:
    """Check if the configured model is available on the LLM provider."""
    if _validate_provider(config) == "openai":
        return check_openai_model_available(config)
    return check_model_available(config)


def query_llm(prompt: str, config: Config) -> str:
    """Send a prompt to the configured LLM provider."""
    if _validate_provider(config) == "openai":
        return query_openai(prompt, config)
    return query_ollama(prompt, config)


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
