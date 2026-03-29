"""Job model, in-memory store, and pipeline runner."""

import asyncio
import logging
import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from api.config import Config
from api.db import MeetingRepository

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


@dataclass
class Job:
    id: str
    status: JobStatus = JobStatus.queued
    progress: str = "Waiting to start"
    phase: str = "transcription"  # "transcription" or "summary"
    notes_markdown: str | None = None
    error: str | None = None
    source_filename: str = ""
    template_id: int | None = None
    meeting_id: int | None = None
    _events: asyncio.Queue = field(default_factory=asyncio.Queue, repr=False)

    def push_event(self, event: str) -> None:
        self.progress = event
        try:
            self._events.put_nowait(event)
        except asyncio.QueueFull:
            pass


# In-memory job store (single-process; swap for Redis/DB for production)
_jobs: dict[str, Job] = {}


def get_jobs_store() -> dict[str, Job]:
    """Return the jobs store. Exposed for testing."""
    return _jobs


def run_transcription(
    job: Job, file_path: Path, config: Config, repo: MeetingRepository,
) -> None:
    """Phase 1: Transcribe audio and save transcript to DB."""
    from api.audio import extract_audio, get_duration, validate_input
    from api.markdown import build_sidecar_dict, render, write_output
    from api.quality import analyze_quality
    from api.transcribe import transcribe

    job.status = JobStatus.processing
    repo.update_job(job.id, status="processing", phase="transcription")

    # Step 1: Validate
    job.push_event("Validating input file")
    file_type = validate_input(file_path)

    # Step 2: Duration
    job.push_event("Reading file info")
    duration = get_duration(file_path)

    # Step 3: Extract audio
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        if file_type == "video":
            job.push_event("Extracting audio from video")
        else:
            job.push_event("Preparing audio")
        audio_path = extract_audio(file_path, tmp_path)

        # Step 4: Transcribe
        job.push_event("Transcribing audio")

        def transcribe_callback(msg: str) -> None:
            job.push_event(msg)

        transcript = transcribe(audio_path, config, progress_callback=transcribe_callback)

        if not transcript.segments:
            raise RuntimeError("No speech detected in the audio file")

        # Step 5: Quality analysis
        job.push_event("Analyzing audio quality")
        quality_flags = analyze_quality(transcript)

    # Step 6: Render transcript-only markdown
    job.push_event("Saving transcript")
    content = render(
        source_file=file_path,
        duration=duration,
        transcript=transcript,
        extraction=None,
        quality_flags=quality_flags,
        config=config,
    )

    # Step 7: Write output and persist to database
    output_dir = Path(config.default_output_dir)
    sidecar = build_sidecar_dict(
        source_file=file_path,
        duration=duration,
        transcript=transcript,
        extraction=None,
        quality_flags=quality_flags,
        config=config,
    )
    output_path = write_output(content, output_dir)
    job.notes_markdown = content

    sidecar.setdefault("filename", output_path.name)
    meeting_id = repo.save_meeting(sidecar, content, job_id=job.id)

    # Step 8: Save transcript segments to dedicated table
    repo.save_transcript_segments(meeting_id, transcript.segments)

    job.meeting_id = meeting_id
    repo.update_job(job.id, meeting_id=meeting_id)


def run_summary(
    job: Job, config: Config, repo: MeetingRepository,
) -> None:
    """Phase 2: Run LLM extraction on stored transcript and update meeting."""
    from api.extractor import extract_from_transcript
    from api.llm import check_llm, check_llm_model_available
    from api.markdown import build_sidecar_dict, render
    from api.quality import QualityFlag
    from api.transcribe import TranscriptResult

    repo.update_job(job.id, phase="summary")

    # Check LLM availability
    job.push_event("Checking LLM availability")
    if not (check_llm(config) and check_llm_model_available(config)):
        job.push_event("LLM not available, skipping summary")
        return

    # Load transcript segments from DB
    segments = repo.get_transcript_segments(job.meeting_id)
    if not segments:
        job.push_event("No transcript segments found, skipping summary")
        return

    # Load meeting metadata for re-rendering
    meeting_row = repo.get_meeting_metadata_by_id(job.meeting_id)

    # Look up custom template prompt if one was selected
    prompt_text = None
    if job.template_id is not None:
        template = repo.get_template(job.template_id)
        if template and not template["is_default"]:
            prompt_text = template["prompt_text"]

    # Run LLM extraction
    job.push_event("Running LLM extraction")

    def llm_callback(current: int, total: int) -> None:
        job.push_event(f"LLM extraction (chunk {current}/{total})")

    extraction = extract_from_transcript(
        segments, config, progress_callback=llm_callback,
        prompt_text=prompt_text,
    )

    # Re-render full markdown with extraction results
    job.push_event("Generating notes")

    # Reconstruct TranscriptResult for rendering
    speakers = set(seg.speaker for seg in segments)
    transcript = TranscriptResult(
        segments=segments,
        speaker_count=len(speakers),
    )

    # Reconstruct quality flags from stored meeting data
    quality_flags = []
    if meeting_row and meeting_row.get("quality_flags"):
        quality_flags = [
            QualityFlag(type=f["type"], timestamp=f["timestamp"], description=f["description"])
            for f in meeting_row["quality_flags"]
        ]

    source_file = Path(meeting_row["audio_file"]) if meeting_row else Path("unknown")

    # Parse duration back to seconds for rendering
    duration_str = meeting_row.get("duration", "0m 00s") if meeting_row else "0m 00s"
    duration = _parse_duration(duration_str)

    content = render(
        source_file=source_file,
        duration=duration,
        transcript=transcript,
        extraction=extraction,
        quality_flags=quality_flags,
        config=config,
    )

    # Build sidecar for DB update
    sidecar = build_sidecar_dict(
        source_file=source_file,
        duration=duration,
        transcript=transcript,
        extraction=extraction,
        quality_flags=quality_flags,
        config=config,
    )

    # Update meeting in DB
    repo.update_meeting_extraction(job.meeting_id, sidecar, content)
    job.notes_markdown = content


def _parse_duration(duration_str: str) -> float:
    """Parse a duration string like '5m 30s' or '1h 05m 30s' back to seconds."""
    total = 0.0
    h = re.search(r"(\d+)h", duration_str)
    m = re.search(r"(\d+)m", duration_str)
    s = re.search(r"(\d+)s", duration_str)
    if h:
        total += int(h.group(1)) * 3600
    if m:
        total += int(m.group(1)) * 60
    if s:
        total += int(s.group(1))
    return total


async def process_resummarize_job(
    job: Job, config: Config, repo: MeetingRepository,
) -> None:
    """Run summary phase as a standalone job (used by the resummarize endpoint)."""
    try:
        loop = asyncio.get_event_loop()
        job.status = JobStatus.processing
        repo.update_job(job.id, status="processing", phase="summary")
        await loop.run_in_executor(None, run_summary, job, config, repo)
        job.status = JobStatus.completed
        job.push_event("Complete")
        repo.update_job(job.id, status="completed", notes_markdown=job.notes_markdown)
    except Exception as e:
        job.status = JobStatus.failed
        job.error = str(e)
        job.push_event(f"Failed: {e}")
        repo.update_job(job.id, status="failed", error=str(e))


async def process_job(
    job: Job, file_path: Path, config: Config, repo: MeetingRepository,
) -> None:
    """Run both pipeline phases in a thread so we don't block the event loop."""
    try:
        loop = asyncio.get_event_loop()

        # Phase 1: Transcription
        job.phase = "transcription"
        await loop.run_in_executor(None, run_transcription, job, file_path, config, repo)

        # Phase 2: Summary (graceful — transcript survives if this fails)
        try:
            job.phase = "summary"
            await loop.run_in_executor(None, run_summary, job, config, repo)
        except Exception as e:
            job.push_event(f"Summary skipped: {e}")
            repo.update_job(job.id, phase="summary_skipped", error=f"Summary failed: {e}")

        job.status = JobStatus.completed
        job.push_event("Complete")
        repo.update_job(job.id, status="completed", notes_markdown=job.notes_markdown)
    except Exception as e:
        job.status = JobStatus.failed
        job.error = str(e)
        job.push_event(f"Failed: {e}")
        repo.update_job(job.id, status="failed", error=str(e))
    finally:
        # Clean up the uploaded temp file
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to clean up temp file %s", file_path, exc_info=True)
