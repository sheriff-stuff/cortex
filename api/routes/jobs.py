"""Job-related API routes."""

import asyncio
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Form, HTTPException, UploadFile
from sse_starlette.sse import EventSourceResponse

from api.audio import SUPPORTED_ALL
from api.config import Config
from api.db import MeetingRepository
from api.jobs import Job, JobStatus, _jobs, process_job, process_resummarize_job
from api.responses import job_status_dict


def create_router(config: Config, repo: MeetingRepository) -> APIRouter:
    router = APIRouter()

    @router.post("/jobs", status_code=202)
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

    @router.get("/jobs")
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

    @router.get("/jobs/{job_id}")
    async def get_job_status(job_id: str) -> dict:
        """Get the current status and progress of a job."""
        job = _jobs.get(job_id)
        if job:
            return job_status_dict(job)

        db_job = repo.get_job(job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job_status_dict(db_job)

    @router.get("/jobs/{job_id}/notes")
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

    @router.get("/jobs/{job_id}/events")
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

    @router.post("/jobs/{job_id}/resummarize", status_code=202)
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

    return router
