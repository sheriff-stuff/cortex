"""Tests for the MeetingRepository database layer."""

import pytest

pytest.importorskip("sqlalchemy")


class TestJobCrud:
    def test_create_and_get_job(self, repo):
        repo.create_job("job001", "meeting.wav", template_id=None)
        job = repo.get_job("job001")
        assert job is not None
        assert job["id"] == "job001"
        assert job["status"] == "queued"
        assert job["source_filename"] == "meeting.wav"
        assert job["progress"] == "Waiting to start"

    def test_get_nonexistent_job(self, repo):
        assert repo.get_job("nonexistent") is None

    def test_update_job(self, repo):
        repo.create_job("job002", "test.wav")
        repo.update_job("job002", status="processing", progress="Transcribing...")
        job = repo.get_job("job002")
        assert job["status"] == "processing"
        assert job["progress"] == "Transcribing..."

    def test_fail_orphaned_jobs(self, repo):
        repo.create_job("j1", "a.wav")
        repo.create_job("j2", "b.wav")
        repo.update_job("j2", status="processing")
        repo.create_job("j3", "c.wav")
        repo.update_job("j3", status="completed")

        count = repo.fail_orphaned_jobs()
        assert count == 2  # j1 (queued) and j2 (processing)

        assert repo.get_job("j1")["status"] == "failed"
        assert repo.get_job("j2")["status"] == "failed"
        assert repo.get_job("j3")["status"] == "completed"

    def test_create_job_with_template(self, repo):
        repo.create_job("job003", "test.wav", template_id=42)
        job = repo.get_job("job003")
        assert job["template_id"] == 42


class TestMeetingCrud:
    def test_save_and_get_meeting(self, repo, sample_sidecar):
        sidecar = sample_sidecar()
        meeting_id = repo.save_meeting(sidecar, "# Meeting Notes", job_id="j1")
        assert meeting_id is not None

        result = repo.get_meeting_by_filename("test-meeting.wav")
        assert result is not None
        assert result["filename"] == "test-meeting.wav"
        assert result["metadata"]["speakers"] == 3
        assert result["summary"]["topic_count"] == 1
        assert result["overview"] == "Test meeting overview"
        assert len(result["topics"]) == 1
        assert len(result["decisions"]) == 1

    def test_meeting_exists(self, repo, sample_sidecar):
        assert repo.meeting_exists("no-such-file.wav") is False
        repo.save_meeting(sample_sidecar(), "md")
        assert repo.meeting_exists("test-meeting.wav") is True

    def test_list_meetings(self, repo, sample_sidecar):
        assert repo.list_meetings() == []
        repo.save_meeting(sample_sidecar(filename="a.wav"), "md")
        repo.save_meeting(sample_sidecar(filename="b.wav"), "md")
        meetings = repo.list_meetings()
        assert len(meetings) == 2
        assert "filename" in meetings[0]
        assert "speakers" in meetings[0]

    def test_update_meeting_extraction(self, repo, sample_sidecar):
        sidecar = sample_sidecar(topics=[], decisions=[], action_items=[], questions=[])
        mid = repo.save_meeting(sidecar, "md")

        updated_sidecar = sample_sidecar(
            topics=[{"title": "New Topic", "timestamp": "00:00"}],
            overview="Updated overview",
            keywords=["new"],
        )
        repo.update_meeting_extraction(mid, updated_sidecar, "# Updated")

        result = repo.get_meeting_by_filename("test-meeting.wav")
        assert result["overview"] == "Updated overview"
        assert len(result["topics"]) == 1
        assert result["topics"][0]["title"] == "New Topic"
        assert result["keywords"] == ["new"]

    def test_get_meeting_markdown(self, repo, sample_sidecar):
        repo.save_meeting(sample_sidecar(), "# The markdown content")
        md = repo.get_meeting_markdown("test-meeting.wav")
        assert md == "# The markdown content"

    def test_get_meeting_markdown_not_found(self, repo):
        assert repo.get_meeting_markdown("nope.wav") is None

    def test_get_meeting_id_by_job(self, repo, sample_sidecar):
        repo.save_meeting(sample_sidecar(), "md", job_id="jx1")
        mid = repo.get_meeting_id_by_job("jx1")
        assert mid is not None
        assert repo.get_meeting_id_by_job("nonexistent") is None

    def test_quality_flags_round_trip(self, repo, sample_sidecar):
        flags = [
            {"type": "low_confidence", "timestamp": "02:30", "description": "Low confidence segment"},
            {"type": "overlap", "timestamp": "05:00", "description": "Overlapping speech"},
        ]
        sidecar = sample_sidecar()
        sidecar["metadata"]["quality_flags"] = flags
        repo.save_meeting(sidecar, "md")

        result = repo.get_meeting_by_filename("test-meeting.wav")
        meta = result["metadata"]
        assert "quality_flags" in meta
        assert len(meta["quality_flags"]) == 2
        assert meta["quality_flags"][0]["type"] == "low_confidence"
        assert meta["quality_flags"][1]["description"] == "Overlapping speech"


class TestSpeakerNames:
    def test_save_and_get(self, repo, sample_sidecar):
        mid = repo.save_meeting(sample_sidecar(), "md")
        repo.save_speaker_names(mid, {"Speaker 1": "Alice", "Speaker 2": "Bob"})
        names = repo.get_speaker_names(mid)
        assert names == {"Speaker 1": "Alice", "Speaker 2": "Bob"}

    def test_empty_values_filtered(self, repo, sample_sidecar):
        mid = repo.save_meeting(sample_sidecar(), "md")
        repo.save_speaker_names(mid, {"Speaker 1": "Alice", "Speaker 2": ""})
        names = repo.get_speaker_names(mid)
        assert names == {"Speaker 1": "Alice"}

    def test_replace_on_second_save(self, repo, sample_sidecar):
        mid = repo.save_meeting(sample_sidecar(), "md")
        repo.save_speaker_names(mid, {"Speaker 1": "Alice"})
        repo.save_speaker_names(mid, {"Speaker 1": "Bob", "Speaker 2": "Charlie"})
        names = repo.get_speaker_names(mid)
        assert names == {"Speaker 1": "Bob", "Speaker 2": "Charlie"}

    def test_empty_for_no_names(self, repo, sample_sidecar):
        mid = repo.save_meeting(sample_sidecar(), "md")
        assert repo.get_speaker_names(mid) == {}


class TestTranscriptSegments:
    def test_save_and_get(self, repo, sample_sidecar, sample_segments):
        mid = repo.save_meeting(sample_sidecar(), "md")
        repo.save_transcript_segments(mid, sample_segments)
        loaded = repo.get_transcript_segments(mid)
        assert len(loaded) == 4
        assert loaded[0].speaker == "Speaker 1"
        assert loaded[0].text == "Hello everyone."
        assert loaded[0].confidence == 0.95


class TestTemplateCrud:
    def test_default_template_seeded(self, repo):
        templates = repo.list_templates()
        assert len(templates) >= 1
        default = [t for t in templates if t["is_default"]]
        assert len(default) == 1
        assert default[0]["name"] == "Default Extraction"

    def test_create_and_get_template(self, repo):
        tid = repo.create_template("Custom", "My template", "Extract topics only")
        tmpl = repo.get_template(tid)
        assert tmpl["name"] == "Custom"
        assert tmpl["prompt_text"] == "Extract topics only"
        assert tmpl["is_default"] == 0

    def test_duplicate_template(self, repo):
        tid = repo.create_template("Original", "Desc", "prompt")
        new_id = repo.duplicate_template(tid)
        assert new_id is not None
        copy = repo.get_template(new_id)
        assert copy["name"] == "Original (copy)"
        assert copy["prompt_text"] == "prompt"

    def test_duplicate_nonexistent(self, repo):
        assert repo.duplicate_template(9999) is None

    def test_delete_template(self, repo):
        tid = repo.create_template("ToDelete", "", "prompt")
        repo.delete_template(tid)
        assert repo.get_template(tid) is None

    def test_update_template(self, repo):
        tid = repo.create_template("Old Name", "", "old prompt")
        repo.update_template(tid, name="New Name", prompt_text="new prompt")
        tmpl = repo.get_template(tid)
        assert tmpl["name"] == "New Name"
        assert tmpl["prompt_text"] == "new prompt"
