"""Audio quality analysis and transcription confidence checking."""

from dataclasses import dataclass

from api.transcribe import TranscriptResult

MIN_CONFIDENCE = 0.5
OVERLAP_TOLERANCE_SECONDS = 0.5
SILENCE_GAP_THRESHOLD_SECONDS = 10.0


@dataclass
class QualityFlag:
    type: str
    timestamp: str
    description: str


def _format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _format_range(start: float, end: float) -> str:
    return f"{_format_timestamp(start)}-{_format_timestamp(end)}"


def analyze_quality(result: TranscriptResult) -> list[QualityFlag]:
    """Analyze transcript for quality issues."""
    flags: list[QualityFlag] = []

    _check_low_confidence(result, flags)
    _check_overlapping_speech(result, flags)
    _check_silence_gaps(result, flags)

    return flags


def _check_low_confidence(result: TranscriptResult, flags: list[QualityFlag]) -> None:
    """Flag segments with low transcription confidence."""
    low_conf_start = None
    low_conf_end = None

    for seg in result.segments:
        if seg.confidence < MIN_CONFIDENCE:
            if low_conf_start is None:
                low_conf_start = seg.start
            low_conf_end = seg.end
        else:
            if low_conf_start is not None:
                flags.append(QualityFlag(
                    type="low_confidence",
                    timestamp=_format_range(low_conf_start, low_conf_end),
                    description="Low transcription confidence, text may be inaccurate",
                ))
                low_conf_start = None
                low_conf_end = None

    # Handle trailing low-confidence region
    if low_conf_start is not None:
        flags.append(QualityFlag(
            type="low_confidence",
            timestamp=_format_range(low_conf_start, low_conf_end),
            description="Low transcription confidence, text may be inaccurate",
        ))


def _check_overlapping_speech(result: TranscriptResult, flags: list[QualityFlag]) -> None:
    """Flag sections where speakers overlap."""
    segments = result.segments
    for i in range(len(segments) - 1):
        curr = segments[i]
        nxt = segments[i + 1]
        if curr.speaker != nxt.speaker and curr.end > nxt.start + OVERLAP_TOLERANCE_SECONDS:
            overlap_start = nxt.start
            overlap_end = min(curr.end, nxt.end)
            flags.append(QualityFlag(
                type="overlapping_speech",
                timestamp=_format_range(overlap_start, overlap_end),
                description="Multiple speakers talking simultaneously, transcription may be incomplete",
            ))


def _check_silence_gaps(result: TranscriptResult, flags: list[QualityFlag]) -> None:
    """Flag long silence gaps (>10 seconds)."""
    for i in range(len(result.segments) - 1):
        curr = result.segments[i]
        nxt = result.segments[i + 1]
        gap = nxt.start - curr.end
        if gap > SILENCE_GAP_THRESHOLD_SECONDS:
            flags.append(QualityFlag(
                type="long_silence",
                timestamp=_format_range(curr.end, nxt.start),
                description=f"Long silence gap ({int(gap)} seconds)",
            ))
