"""Job model, in-memory store, and pipeline runner."""

import asyncio
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from api.config import Config
from api.db import MeetingRepository


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
    notes_markdown: str | None = None
    error: str | None = None
    source_filename: str = ""
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


def run_pipeline(
    job: Job, file_path: Path, config: Config, repo: MeetingRepository,
) -> None:
    """Run the meeting notes pipeline synchronously, updating job progress."""
    from api.audio import extract_audio, get_duration, validate_input
    from api.extractor import extract_from_transcript
    from api.llm import check_model_available, check_ollama
    from api.markdown import build_sidecar_dict, render, write_output
    from api.quality import analyze_quality
    from api.transcribe import transcribe

    job.status = JobStatus.processing
    repo.update_job(job.id, status="processing")

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

        # Step 6: LLM extraction
        extraction = None

        if check_ollama(config) and check_model_available(config):
            job.push_event("Running LLM extraction")

            def llm_callback(current: int, total: int) -> None:
                job.push_event(f"LLM extraction (chunk {current}/{total})")

            extraction = extract_from_transcript(
                transcript.segments, config, progress_callback=llm_callback,
            )
        else:
            job.push_event("Ollama not available, skipping LLM extraction")

        # Step 7: Render
        job.push_event("Generating notes")
        content = render(
            source_file=file_path,
            duration=duration,
            transcript=transcript,
            extraction=extraction,
            quality_flags=quality_flags,
            config=config,
        )

        # Step 8: Write output
        output_dir = Path(config.default_output_dir)
        sidecar = build_sidecar_dict(
            source_file=file_path,
            duration=duration,
            transcript=transcript,
            extraction=extraction,
            quality_flags=quality_flags,
            config=config,
        )
        output_path = write_output(content, output_dir)
        job.notes_markdown = content

        # Step 9: Persist to database
        sidecar.setdefault("filename", output_path.name)
        repo.save_meeting(sidecar, content, job_id=job.id)


async def process_job(
    job: Job, file_path: Path, config: Config, repo: MeetingRepository,
) -> None:
    """Run pipeline in a thread so we don't block the event loop."""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_pipeline, job, file_path, config, repo)
        job.status = JobStatus.completed
        job.push_event("Complete")
        repo.update_job(job.id, status="completed", notes_markdown=job.notes_markdown)
    except Exception as e:
        job.status = JobStatus.failed
        job.error = str(e)
        job.push_event(f"Failed: {e}")
        repo.update_job(job.id, status="failed", error=str(e))
