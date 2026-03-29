"""Tests for audio quality analysis."""

from api.quality import analyze_quality
from api.transcribe import Segment, TranscriptResult


class TestAnalyzeQuality:
    def test_clean_transcript_no_flags(self, sample_transcript):
        flags = analyze_quality(sample_transcript)
        assert flags == []

    def test_low_confidence_flag(self):
        segments = [
            Segment(start=0.0, end=5.0, speaker="Speaker 1", text="Clear audio.", confidence=0.95),
            Segment(start=5.0, end=10.0, speaker="Speaker 1", text="Mumbled words.", confidence=0.3),
            Segment(start=10.0, end=15.0, speaker="Speaker 1", text="Clear again.", confidence=0.9),
        ]
        result = TranscriptResult(segments=segments, speaker_count=1, language="en")
        flags = analyze_quality(result)
        lc = [f for f in flags if f.type == "low_confidence"]
        assert len(lc) == 1
        assert "00:05-00:10" in lc[0].timestamp

    def test_overlapping_speech_flag(self):
        segments = [
            Segment(start=0.0, end=8.0, speaker="Speaker 1", text="Long sentence.", confidence=0.9),
            Segment(start=5.0, end=10.0, speaker="Speaker 2", text="Interrupts.", confidence=0.9),
        ]
        result = TranscriptResult(segments=segments, speaker_count=2, language="en")
        flags = analyze_quality(result)
        overlap = [f for f in flags if f.type == "overlapping_speech"]
        assert len(overlap) == 1

    def test_long_silence_flag(self):
        segments = [
            Segment(start=0.0, end=5.0, speaker="Speaker 1", text="Before silence.", confidence=0.9),
            Segment(start=20.0, end=25.0, speaker="Speaker 1", text="After silence.", confidence=0.9),
        ]
        result = TranscriptResult(segments=segments, speaker_count=1, language="en")
        flags = analyze_quality(result)
        silence = [f for f in flags if f.type == "long_silence"]
        assert len(silence) == 1
        assert "15 seconds" in silence[0].description

    def test_trailing_low_confidence(self):
        """Low confidence at end of transcript is still flagged."""
        segments = [
            Segment(start=0.0, end=5.0, speaker="Speaker 1", text="Clear.", confidence=0.9),
            Segment(start=5.0, end=10.0, speaker="Speaker 1", text="Unclear.", confidence=0.3),
        ]
        result = TranscriptResult(segments=segments, speaker_count=1, language="en")
        flags = analyze_quality(result)
        lc = [f for f in flags if f.type == "low_confidence"]
        assert len(lc) == 1
