"""Tests for API response formatting helpers."""

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")
fastapi = pytest.importorskip("fastapi")

from api.jobs import Job, JobStatus
from api.responses import (
    check_filename,
    format_action_detail,
    format_detail,
    job_status_dict,
    response_from_sidecar,
    transform_items,
)


# --- format_detail ---


class TestFormatDetail:
    def test_two_parts(self):
        assert format_detail("Alice", "05:30") == "Alice, 05:30"

    def test_one_empty(self):
        assert format_detail("Alice", "") == "Alice"

    def test_all_empty(self):
        assert format_detail("", "") == ""

    def test_single_part(self):
        assert format_detail("only") == "only"

    def test_three_parts(self):
        assert format_detail("a", "b", "c") == "a, b, c"


# --- format_action_detail ---


class TestFormatActionDetail:
    def test_speaker_deadline_timestamp(self):
        item = {"speaker": "Alice", "deadline": "Friday", "timestamp": "05:30"}
        assert format_action_detail(item) == "Alice, by Friday (05:30)"

    def test_speaker_only(self):
        item = {"speaker": "Alice"}
        assert format_action_detail(item) == "Alice"

    def test_timestamp_only(self):
        item = {"timestamp": "05:30"}
        assert format_action_detail(item) == "05:30"

    def test_empty_item(self):
        assert format_action_detail({}) == ""

    def test_speaker_and_timestamp(self):
        item = {"speaker": "Bob", "timestamp": "10:00"}
        assert format_action_detail(item) == "Bob (10:00)"

    def test_deadline_and_timestamp(self):
        item = {"deadline": "Monday", "timestamp": "02:00"}
        assert format_action_detail(item) == "by Monday (02:00)"


# --- transform_items ---


class TestTransformItems:
    def test_topics_shape(self):
        topics = [{"title": "A", "description": "Desc", "key_points": ["p1"]}]
        result = transform_items(topics, [], [], [])
        assert result["topics"] == [{"title": "A", "description": "Desc", "key_points": ["p1"]}]

    def test_decisions_shape(self):
        decisions = [{"decision": "Go ahead", "speaker": "Alice", "timestamp": "05:30"}]
        result = transform_items([], decisions, [], [])
        assert result["decisions"] == [{"decision": "Go ahead", "detail": "Alice, 05:30"}]

    def test_action_items_shape(self):
        action_items = [{"task": "Write spec", "speaker": "Bob", "deadline": "Friday", "timestamp": "10:00"}]
        result = transform_items([], [], action_items, [])
        assert result["action_items"] == [{"task": "Write spec", "detail": "Bob, by Friday (10:00)"}]

    def test_questions_shape(self):
        questions = [{"question": "What about testing?", "asker": "Charlie", "timestamp": "15:00"}]
        result = transform_items([], [], [], questions)
        q = result["questions"][0]
        assert q["question"] == "What about testing?"
        assert q["attribution"] == "Charlie, 15:00"
        assert q["answer"] is None
        assert q["answer_attribution"] is None

    def test_questions_with_answer(self):
        questions = [{"question": "Q?", "asker": "A", "timestamp": "01:00", "answer": "Yes", "answerer": "B", "answer_timestamp": "01:10"}]
        result = transform_items([], [], [], questions)
        q = result["questions"][0]
        assert q["answer"] == "Yes"
        assert q["answer_attribution"] == "B, 01:10"

    def test_empty_lists(self):
        result = transform_items([], [], [], [])
        assert result == {"topics": [], "decisions": [], "action_items": [], "questions": []}


# --- check_filename ---


class TestCheckFilename:
    def test_valid_filename(self):
        check_filename("meeting-2025-01-15.wav")  # should not raise

    def test_slash_raises(self):
        with pytest.raises(fastapi.HTTPException) as exc_info:
            check_filename("../../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_backslash_raises(self):
        with pytest.raises(fastapi.HTTPException) as exc_info:
            check_filename("folder\\file.wav")
        assert exc_info.value.status_code == 400

    def test_dotdot_raises(self):
        with pytest.raises(fastapi.HTTPException) as exc_info:
            check_filename("..secret")
        assert exc_info.value.status_code == 400


# --- job_status_dict ---


class TestJobStatusDict:
    def test_from_job_object(self):
        job = Job(id="abc123", source_filename="test.wav")
        result = job_status_dict(job)
        assert result["job_id"] == "abc123"
        assert result["status"] == "queued"
        assert result["source_filename"] == "test.wav"
        assert "error" not in result

    def test_from_job_with_error(self):
        job = Job(id="abc123", status=JobStatus.failed, error="Something broke", source_filename="test.wav")
        result = job_status_dict(job)
        assert result["error"] == "Something broke"
        assert result["status"] == "failed"

    def test_from_db_row(self):
        row = {
            "id": "xyz789",
            "status": "completed",
            "progress": "Done",
            "source_filename": "meeting.wav",
            "phase": "summary",
            "error": None,
        }
        result = job_status_dict(row)
        assert result["job_id"] == "xyz789"
        assert result["status"] == "completed"
        assert "error" not in result


# --- response_from_sidecar ---


class TestResponseFromSidecar:
    def test_basic_shape(self, sample_sidecar):
        sidecar = sample_sidecar()
        result = response_from_sidecar(sidecar, "test-meeting.wav")
        assert result["filename"] == "test-meeting.wav"
        assert result["metadata"]["speakers"] == 3
        assert result["summary"]["topic_count"] == 1
        assert result["overview"] == "Test meeting overview"
        assert len(result["topics"]) == 1
        assert len(result["decisions"]) == 1
        assert len(result["action_items"]) == 1
        assert len(result["questions"]) == 1
