"""Tests for LLM response parsing, deduplication, and merging."""

import pytest

from api.extractor import (
    ExtractionResult,
    _deduplicate_items,
    _jaccard_similarity,
    _timestamp_to_seconds,
    merge_extractions,
    parse_llm_response,
)


# --- parse_llm_response ---


class TestParseLlmResponse:
    def test_clean_json(self):
        result = parse_llm_response('{"overview": "Test"}')
        assert result == {"overview": "Test"}

    def test_markdown_fenced_json(self):
        text = '```json\n{"topics": [{"title": "A"}]}\n```'
        result = parse_llm_response(text)
        assert result == {"topics": [{"title": "A"}]}

    def test_markdown_fence_without_json_tag(self):
        text = '```\n{"key": "value"}\n```'
        result = parse_llm_response(text)
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        text = 'Here is the result:\n{"overview": "Meeting notes"}\nEnd of response.'
        result = parse_llm_response(text)
        assert result == {"overview": "Meeting notes"}

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Could not parse JSON"):
            parse_llm_response("")

    def test_garbage_input_raises(self):
        with pytest.raises(ValueError, match="Could not parse JSON"):
            parse_llm_response("This is not JSON at all, just text.")

    def test_nested_json(self):
        text = '{"topics": [{"title": "A", "key_points": ["p1", "p2"]}]}'
        result = parse_llm_response(text)
        assert len(result["topics"]) == 1
        assert result["topics"][0]["key_points"] == ["p1", "p2"]


# --- _timestamp_to_seconds ---


class TestTimestampToSeconds:
    def test_mm_ss(self):
        assert _timestamp_to_seconds("05:30") == 330.0

    def test_hh_mm_ss(self):
        assert _timestamp_to_seconds("01:05:30") == 3930.0

    def test_zero(self):
        assert _timestamp_to_seconds("00:00") == 0.0

    def test_invalid_returns_zero(self):
        assert _timestamp_to_seconds("invalid") == 0.0

    def test_empty_returns_zero(self):
        assert _timestamp_to_seconds("") == 0.0


# --- _jaccard_similarity ---


class TestJaccardSimilarity:
    def test_identical_strings(self):
        assert _jaccard_similarity("hello world", "hello world") == 1.0

    def test_disjoint_strings(self):
        assert _jaccard_similarity("hello world", "foo bar") == 0.0

    def test_partial_overlap(self):
        # "hello world" and "hello foo" share "hello" out of {"hello", "world", "foo"}
        result = _jaccard_similarity("hello world", "hello foo")
        assert abs(result - 1 / 3) < 0.01

    def test_empty_string_returns_zero(self):
        assert _jaccard_similarity("", "hello") == 0.0

    def test_both_empty_returns_zero(self):
        assert _jaccard_similarity("", "") == 0.0


# --- _deduplicate_items ---


class TestDeduplicateItems:
    def test_empty_list(self):
        assert _deduplicate_items([], "title") == []

    def test_no_duplicates(self):
        items = [
            {"title": "Topic A", "timestamp": "01:00"},
            {"title": "Topic B", "timestamp": "30:00"},
        ]
        result = _deduplicate_items(items, "title")
        assert len(result) == 2

    def test_duplicate_removed(self):
        items = [
            {"title": "Discuss the project roadmap", "timestamp": "05:00"},
            {"title": "Discuss the project roadmap plan", "timestamp": "05:30"},
        ]
        result = _deduplicate_items(items, "title")
        assert len(result) == 1

    def test_far_timestamps_kept(self):
        items = [
            {"title": "Discuss the project roadmap", "timestamp": "05:00"},
            {"title": "Discuss the project roadmap", "timestamp": "50:00"},
        ]
        result = _deduplicate_items(items, "title")
        assert len(result) == 2

    def test_different_text_kept(self):
        items = [
            {"title": "Alpha beta gamma", "timestamp": "05:00"},
            {"title": "Completely different topic", "timestamp": "05:30"},
        ]
        result = _deduplicate_items(items, "title")
        assert len(result) == 2


# --- merge_extractions ---


class TestMergeExtractions:
    def test_single_chunk(self):
        chunks = [{"overview": "Summary", "topics": [{"title": "A", "timestamp": "00:00"}], "keywords": ["ai"]}]
        result = merge_extractions(chunks)
        assert result.overview == "Summary"
        assert len(result.topics) == 1
        assert result.keywords == ["ai"]

    def test_overview_from_first_nonempty(self):
        chunks = [
            {"overview": "", "topics": []},
            {"overview": "Second chunk overview", "topics": []},
        ]
        result = merge_extractions(chunks)
        assert result.overview == "Second chunk overview"

    def test_keyword_case_insensitive_dedup(self):
        chunks = [
            {"keywords": ["AI", "Machine Learning"]},
            {"keywords": ["ai", "Deep Learning"]},
        ]
        result = merge_extractions(chunks)
        assert len(result.keywords) == 3
        assert result.keywords[0] == "AI"  # first occurrence preserved

    def test_merge_multiple_chunks_no_duplicates(self):
        chunks = [
            {"topics": [{"title": "Topic A", "timestamp": "01:00"}], "decisions": []},
            {"topics": [{"title": "Topic B", "timestamp": "30:00"}], "decisions": [{"decision": "Go ahead", "timestamp": "31:00"}]},
        ]
        result = merge_extractions(chunks)
        assert len(result.topics) == 2
        assert len(result.decisions) == 1

    def test_merge_deduplicates_across_chunks(self):
        chunks = [
            {"action_items": [{"task": "Write the technical spec document", "timestamp": "10:00"}]},
            {"action_items": [{"task": "Write the technical spec document draft", "timestamp": "10:30"}]},
        ]
        result = merge_extractions(chunks)
        assert len(result.action_items) == 1

    def test_empty_chunks(self):
        result = merge_extractions([])
        assert result == ExtractionResult()
