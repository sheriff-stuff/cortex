"""Shared fixtures for backend tests."""

import pytest

from api.transcribe import Segment, TranscriptResult


def _make_sidecar(
    filename="test-meeting.wav",
    topics=None,
    decisions=None,
    action_items=None,
    questions=None,
    keywords=None,
    overview="Test meeting overview",
):
    """Build a realistic sidecar dict."""
    return {
        "filename": filename,
        "metadata": {
            "meeting_date": "2025-01-15",
            "meeting_time": "10:00",
            "duration": "45m 0s",
            "speakers": 3,
            "audio_file": filename,
            "processing_date": "2025-01-15T12:00:00Z",
            "whisper_model": "large-v3",
            "llm_model": "qwen2.5-coder:32b",
        },
        "summary": {
            "topic_count": len(topics or []),
            "decision_count": len(decisions or []),
            "action_item_count": len(action_items or []),
            "question_count": len(questions or []),
        },
        "overview": overview,
        "keywords": keywords or ["testing", "automation"],
        "topics": topics or [{"title": "Project Roadmap", "description": "Discussed roadmap", "key_points": ["Timeline set"]}],
        "decisions": decisions or [{"decision": "Ship v2 by March", "speaker": "Alice", "timestamp": "05:30"}],
        "action_items": action_items or [{"task": "Write the tech spec", "speaker": "Bob", "deadline": "Friday", "timestamp": "10:00"}],
        "questions": questions or [{"question": "What about testing?", "asker": "Charlie", "timestamp": "15:00"}],
    }


@pytest.fixture()
def sample_sidecar():
    """Factory fixture returning sidecar dicts."""
    return _make_sidecar


@pytest.fixture()
def sample_segments():
    """List of Segment instances for transcript tests."""
    return [
        Segment(start=0.0, end=5.0, speaker="Speaker 1", text="Hello everyone.", confidence=0.95),
        Segment(start=5.5, end=12.0, speaker="Speaker 2", text="Thanks for joining.", confidence=0.90),
        Segment(start=12.5, end=20.0, speaker="Speaker 1", text="Let's discuss the roadmap.", confidence=0.85),
        Segment(start=20.5, end=30.0, speaker="Speaker 3", text="I have some concerns.", confidence=0.80),
    ]


@pytest.fixture()
def sample_transcript(sample_segments):
    """TranscriptResult with sample segments."""
    return TranscriptResult(
        segments=sample_segments,
        speaker_count=3,
        language="en",
    )


# --- Fixtures that require fastapi/sqlalchemy (for DB and route tests) ---

@pytest.fixture()
def engine():
    """In-memory SQLite engine with all tables created."""
    from api.db import create_db_engine, init_db

    eng = create_db_engine("sqlite:///:memory:")
    init_db(eng)
    return eng


@pytest.fixture()
def repo(engine):
    """MeetingRepository backed by in-memory SQLite."""
    from api.db import MeetingRepository

    return MeetingRepository(engine)


@pytest.fixture()
def config():
    """Minimal Config for testing (in-memory DB, no real services)."""
    from api.config import Config

    return Config(database_url="sqlite:///:memory:")


@pytest.fixture()
def client(config):
    """FastAPI TestClient with in-memory DB."""
    from starlette.testclient import TestClient

    from api.api import create_app

    app = create_app(config)
    with TestClient(app) as c:
        yield c
