"""Parse LLM JSON responses, merge and deduplicate chunk results."""

import json
import re
import warnings
from dataclasses import dataclass, field
from typing import Callable

from api.config import Config
from api.llm import chunk_transcript, query_ollama
from api.prompts import build_extraction_prompt, format_transcript_for_llm
from api.transcribe import Segment


@dataclass
class ExtractionResult:
    overview: str = ""
    topics: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    action_items: list[dict] = field(default_factory=list)
    questions: list[dict] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


def parse_llm_response(response: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = response.strip()

    # Try to extract JSON from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object in the text
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}...")


def _timestamp_to_seconds(ts: str) -> float:
    """Convert MM:SS timestamp to seconds."""
    try:
        parts = ts.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, AttributeError):
        pass
    return 0.0


def _word_set(text: str) -> set[str]:
    """Get normalized word set for similarity comparison."""
    return set(text.lower().split())


def _jaccard_similarity(a: str, b: str) -> float:
    """Jaccard similarity between two strings' word sets."""
    set_a = _word_set(a)
    set_b = _word_set(b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def _deduplicate_items(items: list[dict], text_key: str, time_threshold: float = 60.0, sim_threshold: float = 0.6) -> list[dict]:
    """Remove duplicate items based on timestamp proximity and text similarity."""
    if not items:
        return []

    unique: list[dict] = []
    for item in items:
        item_ts = _timestamp_to_seconds(item.get("timestamp", "00:00"))
        item_text = item.get(text_key, "")
        is_dup = False

        for existing in unique:
            existing_ts = _timestamp_to_seconds(existing.get("timestamp", "00:00"))
            existing_text = existing.get(text_key, "")

            if (abs(item_ts - existing_ts) < time_threshold
                    and _jaccard_similarity(item_text, existing_text) > sim_threshold):
                is_dup = True
                break

        if not is_dup:
            unique.append(item)

    return unique


def merge_extractions(chunk_results: list[dict]) -> ExtractionResult:
    """Merge and deduplicate extraction results from multiple chunks."""
    overview = ""
    all_topics = []
    all_decisions = []
    all_action_items = []
    all_questions = []
    all_keywords: list[str] = []

    for result in chunk_results:
        if not overview and result.get("overview"):
            overview = result["overview"]
        all_topics.extend(result.get("topics", []))
        all_decisions.extend(result.get("decisions", []))
        all_action_items.extend(result.get("action_items", []))
        all_questions.extend(result.get("questions", []))
        all_keywords.extend(result.get("keywords", []))

    # Deduplicate keywords (case-insensitive)
    seen_kw: set[str] = set()
    unique_keywords: list[str] = []
    for kw in all_keywords:
        lower = kw.lower()
        if lower not in seen_kw:
            seen_kw.add(lower)
            unique_keywords.append(kw)

    return ExtractionResult(
        overview=overview,
        topics=_deduplicate_items(all_topics, "title"),
        decisions=_deduplicate_items(all_decisions, "decision"),
        action_items=_deduplicate_items(all_action_items, "task"),
        questions=_deduplicate_items(all_questions, "question"),
        keywords=unique_keywords,
    )


def extract_from_transcript(
    segments: list[Segment],
    config: Config,
    progress_callback: Callable[[int, int], None] | None = None,
    prompt_text: str | None = None,
) -> ExtractionResult:
    """Run full extraction pipeline: chunk -> LLM -> parse -> merge."""
    chunks = chunk_transcript(segments, config)
    chunk_results: list[dict] = []

    for i, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(i + 1, len(chunks))

        transcript_text = format_transcript_for_llm(chunk)
        prompt = build_extraction_prompt(transcript_text, prompt_text=prompt_text)

        # Try up to 2 times
        for attempt in range(2):
            try:
                response = query_ollama(prompt, config)
                parsed = parse_llm_response(response)
                chunk_results.append(parsed)
                break
            except (ValueError, json.JSONDecodeError) as e:
                if attempt == 1:
                    # Second failure: skip this chunk with warning
                    warnings.warn(
                        f"Failed to parse LLM response for chunk {i + 1}: {e}"
                    )

    return merge_extractions(chunk_results)
