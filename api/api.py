"""REST API layer over the meeting notes pipeline."""

import asyncio
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from api.audio import SUPPORTED_ALL
from api.config import Config, load_config
from api.db import MeetingRepository, create_db_engine, init_db
from api.jobs import Job, JobStatus, _jobs, process_job, process_resummarize_job
from api.example_transcript import EXAMPLE_SEGMENTS
from api.extractor import extract_from_transcript
from api.llm import check_ollama
from api.prompts import EXTRACTION_SCHEMA


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



def _transform_items(topics: list, decisions: list, action_items: list, questions: list) -> dict:
    """Transform raw extraction lists into the frontend API shape."""
    return {
        "topics": [
            {
                "title": t.get("title", ""),
                "description": t.get("description", ""),
                "key_points": t.get("key_points", []),
            }
            for t in topics
        ],
        "decisions": [
            {"decision": d.get("decision", ""), "detail": _format_detail(d.get("speaker", ""), d.get("timestamp", ""))}
            for d in decisions
        ],
        "action_items": [
            {"task": a.get("task", ""), "detail": _format_action_detail(a)}
            for a in action_items
        ],
        "questions": [
            {
                "question": q.get("question", ""),
                "attribution": _format_detail(q.get("asker", ""), q.get("timestamp", "")),
                "answer": q.get("answer") or None,
                "answer_attribution": _format_detail(q.get("answerer", ""), q.get("answer_timestamp", "")) or None,
            }
            for q in questions
        ],
    }


def _response_from_sidecar(sidecar: dict, filename: str) -> dict:
    """Transform a sidecar dict into the API contract shape."""
    result = _transform_items(
        sidecar.get("topics", []),
        sidecar.get("decisions", []),
        sidecar.get("action_items", []),
        sidecar.get("questions", []),
    )
    result["filename"] = filename
    result["job_id"] = sidecar.get("job_id")
    result["metadata"] = sidecar["metadata"]
    result["summary"] = sidecar["summary"]
    result["overview"] = sidecar.get("overview", "")
    result["keywords"] = sidecar.get("keywords", [])
    return result


def _job_status_dict(source) -> dict:
    """Build a job status dict from either an in-memory Job or a DB row dict."""
    if isinstance(source, Job):
        result = {
            "job_id": source.id,
            "status": source.status.value,
            "progress": source.progress,
            "source_filename": source.source_filename,
            "phase": source.phase,
        }
        if source.error:
            result["error"] = source.error
        return result

    # DB row (dict)
    result = {
        "job_id": source["id"],
        "status": source["status"],
        "progress": source["progress"],
        "source_filename": source["source_filename"],
        "phase": source.get("phase"),
    }
    if source["error"]:
        result["error"] = source["error"]
    return result


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
    async def upload_audio(
        file: UploadFile, template_id: int | None = Form(None),
    ) -> dict:
        """Upload an audio/video file and start processing."""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        ext = Path(file.filename).suffix.lower()
        if ext not in SUPPORTED_ALL:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_ALL))}",
            )

        if template_id is not None:
            tmpl = repo.get_template(template_id)
            if tmpl is None:
                raise HTTPException(status_code=400, detail="Template not found")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        try:
            shutil.copyfileobj(file.file, tmp)
        finally:
            tmp.close()

        upload_path = Path(tmp.name)

        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, source_filename=file.filename, template_id=template_id)
        _jobs[job_id] = job
        repo.create_job(job_id, file.filename, template_id=template_id)

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
                "phase": j.phase,
            }
            for j in _jobs.values()
            if j.status in (JobStatus.queued, JobStatus.processing)
        ]

    @app.get("/jobs/{job_id}")
    async def get_job_status(job_id: str) -> dict:
        """Get the current status and progress of a job."""
        job = _jobs.get(job_id)
        if job:
            return _job_status_dict(job)

        db_job = repo.get_job(job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="Job not found")
        return _job_status_dict(db_job)

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
        meeting_id = repo.get_meeting_id_by_filename(filename)
        if meeting_id:
            segments = repo.get_transcript_segments(meeting_id)
            result["transcript"] = [
                {
                    "timestamp": f"{int(s.start // 3600):02d}:{int(s.start % 3600 // 60):02d}:{int(s.start % 60):02d}",
                    "speaker": s.speaker,
                    "text": s.text,
                }
                for s in segments
            ]
        else:
            result["transcript"] = []
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

    # --- Template routes ---

    @app.get("/api/templates")
    async def list_templates() -> list[dict]:
        """List all templates (without prompt_text)."""
        return repo.list_templates()

    @app.get("/api/templates/{template_id}")
    async def get_template(template_id: int) -> dict:
        """Get a single template with full prompt_text and the locked schema."""
        tmpl = repo.get_template(template_id)
        if tmpl is None:
            raise HTTPException(status_code=404, detail="Template not found")
        tmpl["schema"] = EXTRACTION_SCHEMA
        return tmpl

    @app.post("/api/templates", status_code=201)
    async def create_template(body: dict) -> dict:
        """Create a new template."""
        name = body.get("name", "").strip()
        description = body.get("description", "").strip()
        prompt_text = body.get("prompt_text", "")

        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        if not prompt_text:
            raise HTTPException(status_code=400, detail="prompt_text is required")
        new_id = repo.create_template(name, description, prompt_text)
        tmpl = repo.get_template(new_id)
        tmpl["schema"] = EXTRACTION_SCHEMA
        return tmpl

    @app.post("/api/templates/render-example")
    async def render_example(body: dict) -> dict:
        """Run extraction on a hardcoded example transcript using the given prompt."""
        prompt_text = body.get("prompt_text", "").strip()
        if not prompt_text:
            raise HTTPException(status_code=400, detail="prompt_text is required")

        if not check_ollama(config):
            raise HTTPException(
                status_code=503,
                detail="Ollama is not available. Please ensure it is running.",
            )

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: extract_from_transcript(
                    EXAMPLE_SEGMENTS, config, prompt_text=prompt_text,
                ),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"LLM extraction failed: {exc}",
            )

        return _transform_items(
            result.topics, result.decisions,
            result.action_items, result.questions,
        )

    @app.put("/api/templates/{template_id}")
    async def update_template(template_id: int, body: dict) -> dict:
        """Update an existing template. Cannot update the default template."""
        tmpl = repo.get_template(template_id)
        if tmpl is None:
            raise HTTPException(status_code=404, detail="Template not found")
        if tmpl["is_default"]:
            raise HTTPException(
                status_code=403, detail="Cannot edit the default template",
            )

        fields: dict = {}
        if "name" in body:
            name = body["name"].strip()
            if not name:
                raise HTTPException(status_code=400, detail="name cannot be empty")
            fields["name"] = name
        if "description" in body:
            fields["description"] = body["description"].strip()
        if "prompt_text" in body:
            fields["prompt_text"] = body["prompt_text"]

        if fields:
            repo.update_template(template_id, **fields)

        updated = repo.get_template(template_id)
        updated["schema"] = EXTRACTION_SCHEMA
        return updated

    @app.delete("/api/templates/{template_id}", status_code=204)
    async def delete_template(template_id: int) -> None:
        """Delete a template. Cannot delete the default template."""
        tmpl = repo.get_template(template_id)
        if tmpl is None:
            raise HTTPException(status_code=404, detail="Template not found")
        if tmpl["is_default"]:
            raise HTTPException(
                status_code=403, detail="Cannot delete the default template",
            )
        repo.delete_template(template_id)

    @app.post("/api/templates/{template_id}/duplicate", status_code=201)
    async def duplicate_template(template_id: int) -> dict:
        """Duplicate a template."""
        new_id = repo.duplicate_template(template_id)
        if new_id is None:
            raise HTTPException(status_code=404, detail="Template not found")
        tmpl = repo.get_template(new_id)
        tmpl["schema"] = EXTRACTION_SCHEMA
        return tmpl

    # --- Re-summarize endpoint ---

    @app.post("/jobs/{job_id}/resummarize", status_code=202)
    async def resummarize(job_id: str, template_id: int | None = None) -> dict:
        """Re-run summary phase for an existing transcript."""
        meeting_id = repo.get_meeting_id_by_job(job_id)
        if meeting_id is None:
            raise HTTPException(status_code=404, detail="No meeting found for this job")

        if template_id is not None:
            tmpl = repo.get_template(template_id)
            if tmpl is None:
                raise HTTPException(status_code=400, detail="Template not found")

        new_job_id = uuid.uuid4().hex[:12]
        new_job = Job(
            id=new_job_id,
            phase="summary",
            source_filename="(re-summarize)",
            template_id=template_id,
            meeting_id=meeting_id,
        )
        _jobs[new_job_id] = new_job
        repo.create_job(new_job_id, "(re-summarize)", template_id=template_id)

        asyncio.create_task(process_resummarize_job(new_job, config, repo))
        return {"job_id": new_job_id, "status": "queued"}

    # --- Test-only seed endpoint (only available with in-memory DB) ---
    if ":memory:" in config.database_url:

        @app.post("/api/test/seed-meeting", status_code=201)
        async def seed_meeting(body: dict) -> dict:
            """Seed a meeting for E2E tests. Only available with in-memory DB."""
            sidecar = body.get("sidecar")
            if not isinstance(sidecar, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Field 'sidecar' is required and must be an object",
                )
            meeting_id = repo.save_meeting(
                sidecar, body.get("markdown", ""), body.get("job_id"),
            )
            return {"meeting_id": meeting_id, "filename": sidecar.get("filename", "")}

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
        cli_overrides=cli_overrides,
    )
    return create_app(config)
