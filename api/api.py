"""REST API layer over the meeting notes pipeline."""

import asyncio
import re
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from api.audio import SUPPORTED_ALL
from api.config import Config, load_config
from api.db import MeetingRepository, create_db_engine, init_db
from api.jobs import Job, JobStatus, _jobs, process_job


# ---------------------------------------------------------------------------
# Response formatting helpers
# ---------------------------------------------------------------------------

def _format_detail(*parts: str) -> str:
    """Join non-empty parts with ', '. Returns '' if all parts are empty."""
    return ", ".join(p for p in parts if p)


def _format_action_detail(item: dict) -> str:
    """Format an action item's detail string to match the API contract."""
    speaker = item.get("speaker", "")
    deadline = item.get("deadline")
    ts = item.get("timestamp", "")
    parts = []
    if speaker:
        parts.append(speaker)
    if deadline:
        parts.append(f"by {deadline}")
    base = ", ".join(parts)
    if ts:
        return f"{base} ({ts})" if base else ts
    return base


def _parse_transcript(markdown: str | None) -> list[dict]:
    """Extract transcript segments from markdown content."""
    if not markdown:
        return []
    section_match = re.search(
        r"## Full Transcript\s*\n(.*?)(?=\n## |\n---|\Z)", markdown, re.DOTALL
    )
    if not section_match:
        return []
    segments = []
    for m in re.finditer(
        r"\*\*\[(\d{2}:\d{2}:\d{2})\]\s+(.+?):\*\*\s*\n(.+?)(?=\n\*\*\[|\Z)",
        section_match.group(1),
        re.DOTALL,
    ):
        segments.append({
            "timestamp": m.group(1),
            "speaker": m.group(2).strip(),
            "text": m.group(3).strip(),
        })
    return segments


def _response_from_sidecar(sidecar: dict, filename: str) -> dict:
    """Transform a sidecar dict into the API contract shape."""
    return {
        "filename": filename,
        "metadata": sidecar["metadata"],
        "summary": sidecar["summary"],
        "topics": [
            {"title": t.get("title", ""), "description": t.get("description", "")}
            for t in sidecar.get("topics", [])
        ],
        "decisions": [
            {"decision": d.get("decision", ""), "detail": _format_detail(d.get("speaker", ""), d.get("timestamp", ""))}
            for d in sidecar.get("decisions", [])
        ],
        "action_items": [
            {"task": a.get("task", ""), "detail": _format_action_detail(a)}
            for a in sidecar.get("action_items", [])
        ],
        "questions": [
            {
                "question": q.get("question", ""),
                "attribution": _format_detail(q.get("asker", ""), q.get("timestamp", "")),
                "answer": q.get("answer") or None,
                "answer_attribution": _format_detail(q.get("answerer", ""), q.get("answer_timestamp", "")) or None,
            }
            for q in sidecar.get("questions", [])
        ],
    }


def _check_filename(filename: str) -> None:
    """Raise 400 if filename looks like a path traversal."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(config: Config | None = None) -> FastAPI:
    """Create the FastAPI application."""
    if config is None:
        config = load_config()

    engine = create_db_engine(config.database_url)
    init_db(engine)
    repo = MeetingRepository(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repo.fail_orphaned_jobs()
        yield

    app = FastAPI(title="Meeting Notes API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Job routes ---

    @app.post("/jobs", status_code=202)
    async def upload_audio(file: UploadFile) -> dict:
        """Upload an audio/video file and start processing."""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        ext = Path(file.filename).suffix.lower()
        if ext not in SUPPORTED_ALL:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_ALL))}",
            )

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        try:
            shutil.copyfileobj(file.file, tmp)
        finally:
            tmp.close()

        upload_path = Path(tmp.name)

        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, source_filename=file.filename)
        _jobs[job_id] = job
        repo.create_job(job_id, file.filename)

        asyncio.create_task(process_job(job, upload_path, config, repo))

        return {"job_id": job_id, "status": job.status.value}

    @app.get("/jobs")
    async def list_active_jobs() -> list[dict]:
        """List all queued/processing jobs."""
        return [
            {
                "job_id": j.id,
                "status": j.status.value,
                "progress": j.progress,
                "source_filename": j.source_filename,
            }
            for j in _jobs.values()
            if j.status in (JobStatus.queued, JobStatus.processing)
        ]

    @app.get("/jobs/{job_id}")
    async def get_job_status(job_id: str) -> dict:
        """Get the current status and progress of a job."""
        job = _jobs.get(job_id)
        if job:
            result = {
                "job_id": job.id,
                "status": job.status.value,
                "progress": job.progress,
                "source_filename": job.source_filename,
            }
            if job.error:
                result["error"] = job.error
            return result

        db_job = repo.get_job(job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="Job not found")

        result = {
            "job_id": db_job["id"],
            "status": db_job["status"],
            "progress": db_job["progress"],
            "source_filename": db_job["source_filename"],
        }
        if db_job["error"]:
            result["error"] = db_job["error"]
        return result

    @app.get("/jobs/{job_id}/notes")
    async def get_job_notes(job_id: str) -> dict:
        """Get the completed meeting notes for a job."""
        job = _jobs.get(job_id)
        if job:
            if job.status == JobStatus.failed:
                raise HTTPException(status_code=422, detail=f"Job failed: {job.error}")
            if job.status != JobStatus.completed:
                raise HTTPException(
                    status_code=409,
                    detail=f"Job not yet completed (status: {job.status.value})",
                )
            return {"job_id": job.id, "markdown": job.notes_markdown}

        db_job = repo.get_job(job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="Job not found")

        if db_job["status"] == "failed":
            raise HTTPException(status_code=422, detail=f"Job failed: {db_job['error']}")
        if db_job["status"] != "completed":
            raise HTTPException(
                status_code=409,
                detail=f"Job not yet completed (status: {db_job['status']})",
            )
        return {"job_id": db_job["id"], "markdown": db_job["notes_markdown"]}

    @app.get("/jobs/{job_id}/events")
    async def job_events(job_id: str) -> EventSourceResponse:
        """SSE stream of real-time progress updates for a job."""
        job = _jobs.get(job_id)
        if not job:
            db_job = repo.get_job(job_id)
            if not db_job:
                raise HTTPException(status_code=404, detail="Job not found")

            async def db_event_generator() -> AsyncGenerator[dict, None]:
                yield {"event": "status", "data": f"{db_job['status']}: {db_job['progress']}"}
                yield {"event": "done", "data": db_job["status"]}

            return EventSourceResponse(db_event_generator())

        async def event_generator() -> AsyncGenerator[dict, None]:
            yield {"event": "status", "data": f"{job.status.value}: {job.progress}"}

            if job.status in (JobStatus.completed, JobStatus.failed):
                return

            while True:
                try:
                    event = await asyncio.wait_for(job._events.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
                    continue

                yield {"event": "progress", "data": event}

                if job.status in (JobStatus.completed, JobStatus.failed):
                    yield {"event": "done", "data": job.status.value}
                    return

        return EventSourceResponse(event_generator())

    # --- Notes routes ---

    @app.get("/api/notes")
    async def list_notes() -> list[dict]:
        """List all saved meeting notes with summary metadata."""
        return repo.list_meetings()

    @app.get("/api/notes/{filename}")
    async def get_note(filename: str) -> dict:
        """Return parsed meeting notes JSON for a meeting."""
        _check_filename(filename)

        db_meeting = repo.get_meeting_by_filename(filename)
        if db_meeting is None:
            raise HTTPException(status_code=404, detail="Note not found")

        result = _response_from_sidecar(db_meeting, filename)
        result["transcript"] = _parse_transcript(db_meeting.get("markdown_content"))
        meeting_id = repo.get_meeting_id_by_filename(filename)
        result["speaker_names"] = repo.get_speaker_names(meeting_id) if meeting_id else {}
        return result

    @app.get("/api/notes/{filename}/speakers")
    async def get_speakers(filename: str) -> dict:
        """Get speaker name mappings for a meeting."""
        _check_filename(filename)

        meeting_id = repo.get_meeting_id_by_filename(filename)
        if meeting_id is None:
            raise HTTPException(status_code=404, detail="Meeting not found")

        return {"speaker_names": repo.get_speaker_names(meeting_id)}

    @app.put("/api/notes/{filename}/speakers")
    async def update_speakers(filename: str, body: dict) -> dict:
        """Save speaker name mappings for a meeting."""
        _check_filename(filename)

        meeting_id = repo.get_meeting_id_by_filename(filename)
        if meeting_id is None:
            raise HTTPException(status_code=404, detail="Meeting not found")

        speaker_names = body.get("speaker_names")
        if not isinstance(speaker_names, dict):
            raise HTTPException(
                status_code=400,
                detail="Request body must contain 'speaker_names' as an object",
            )
        for k, v in speaker_names.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise HTTPException(
                    status_code=400,
                    detail="speaker_names keys and values must be strings",
                )

        repo.save_speaker_names(meeting_id, speaker_names)
        return {"speaker_names": repo.get_speaker_names(meeting_id)}

    return app


def create_app_from_env() -> FastAPI:
    """Factory that reads config from env vars -- used by uvicorn --reload."""
    import os

    config_path = os.environ.get("MEETING_NOTES_CONFIG")
    database_url = os.environ.get("MEETING_NOTES_DATABASE_URL")

    cli_overrides = {}
    if database_url:
        cli_overrides["database_url"] = database_url

    config = load_config(
        config_path=Path(config_path) if config_path else None,
        cli_overrides=cli_overrides or None,
    )
    return create_app(config)
