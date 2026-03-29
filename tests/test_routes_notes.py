"""Integration tests for the notes API routes."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")


class TestListNotes:
    def test_empty_list(self, client):
        resp = client.get("/api/notes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_seeding(self, client, sample_sidecar):
        # Seed via the test endpoint
        sidecar = sample_sidecar(filename="meeting-001.wav")
        resp = client.post("/api/test/seed-meeting", json={"sidecar": sidecar, "markdown": "# Notes"})
        assert resp.status_code == 201

        resp = client.get("/api/notes")
        assert resp.status_code == 200
        notes = resp.json()
        assert len(notes) == 1
        assert notes[0]["filename"] == "meeting-001.wav"
        assert notes[0]["speakers"] == 3


class TestGetNote:
    def _seed(self, client, sample_sidecar, filename="test-meeting.wav"):
        sidecar = sample_sidecar(filename=filename)
        client.post("/api/test/seed-meeting", json={"sidecar": sidecar, "markdown": "# MD"})

    def test_get_note_detail(self, client, sample_sidecar):
        self._seed(client, sample_sidecar)
        resp = client.get("/api/notes/test-meeting.wav")
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test-meeting.wav"
        assert "metadata" in data
        assert "summary" in data
        assert "topics" in data
        assert "decisions" in data
        assert "action_items" in data
        assert "questions" in data
        assert "transcript" in data
        assert "speaker_names" in data

    def test_not_found(self, client):
        resp = client.get("/api/notes/nonexistent.wav")
        assert resp.status_code == 404

    def test_path_traversal_rejected(self, client):
        resp = client.get("/api/notes/..secret")
        assert resp.status_code == 400


class TestSpeakers:
    def _seed(self, client, sample_sidecar):
        sidecar = sample_sidecar(filename="speakers-test.wav")
        client.post("/api/test/seed-meeting", json={"sidecar": sidecar, "markdown": "md"})

    def test_get_speakers_empty(self, client, sample_sidecar):
        self._seed(client, sample_sidecar)
        resp = client.get("/api/notes/speakers-test.wav/speakers")
        assert resp.status_code == 200
        assert resp.json() == {"speaker_names": {}}

    def test_put_and_get_speakers(self, client, sample_sidecar):
        self._seed(client, sample_sidecar)
        resp = client.put(
            "/api/notes/speakers-test.wav/speakers",
            json={"speaker_names": {"Speaker 1": "Alice", "Speaker 2": "Bob"}},
        )
        assert resp.status_code == 200
        assert resp.json()["speaker_names"]["Speaker 1"] == "Alice"

        # Verify via GET
        resp = client.get("/api/notes/speakers-test.wav/speakers")
        assert resp.json()["speaker_names"]["Speaker 2"] == "Bob"

    def test_put_speakers_invalid_body(self, client, sample_sidecar):
        self._seed(client, sample_sidecar)
        resp = client.put("/api/notes/speakers-test.wav/speakers", json={"wrong_key": {}})
        assert resp.status_code == 400

    def test_speakers_not_found(self, client):
        resp = client.get("/api/notes/nonexistent.wav/speakers")
        assert resp.status_code == 404
