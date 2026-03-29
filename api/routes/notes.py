"""Notes and speaker API routes."""

import logging

from fastapi import APIRouter, HTTPException

from api.config import Config
from api.db import MeetingRepository
from api.responses import check_filename, response_from_sidecar

log = logging.getLogger(__name__)


def create_router(config: Config, repo: MeetingRepository) -> APIRouter:
    router = APIRouter(prefix="/api/notes")

    @router.get("")
    async def list_notes() -> list[dict]:
        """List all saved meeting notes with summary metadata."""
        return repo.list_meetings()

    @router.get("/{filename}")
    async def get_note(filename: str) -> dict:
        """Return parsed meeting notes JSON for a meeting."""
        check_filename(filename)

        db_meeting = repo.get_meeting_by_filename(filename)
        if db_meeting is None:
            raise HTTPException(status_code=404, detail="Note not found")

        result = response_from_sidecar(db_meeting, filename)
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

    @router.get("/{filename}/speakers")
    async def get_speakers(filename: str) -> dict:
        """Get speaker name mappings for a meeting."""
        check_filename(filename)

        meeting_id = repo.get_meeting_id_by_filename(filename)
        if meeting_id is None:
            raise HTTPException(status_code=404, detail="Meeting not found")

        return {"speaker_names": repo.get_speaker_names(meeting_id)}

    @router.put("/{filename}/speakers")
    async def update_speakers(filename: str, body: dict) -> dict:
        """Save speaker name mappings for a meeting."""
        check_filename(filename)

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

    @router.put("/{filename}/title")
    async def update_title(filename: str, body: dict) -> dict:
        """Update the title for a meeting."""
        check_filename(filename)

        meeting_id = repo.get_meeting_id_by_filename(filename)
        if meeting_id is None:
            raise HTTPException(status_code=404, detail="Meeting not found")

        title = body.get("title")
        if not isinstance(title, str):
            raise HTTPException(
                status_code=400,
                detail="Request body must contain 'title' as a string",
            )

        title = title.strip()[:500]
        repo.update_title(meeting_id, title)
        return {"title": title}

    @router.post("/backfill-titles")
    def backfill_titles() -> dict:
        """Generate titles for meetings that have an overview but no title."""
        from api.llm import query_ollama

        meetings = repo.get_meetings_without_title()
        updated = 0

        for meeting in meetings:
            overview = meeting["overview"]
            topics = meeting.get("topics", [])
            topic_titles = [t.get("title", "") for t in topics if t.get("title")]

            prompt_parts = [f"Meeting overview: {overview}"]
            if topic_titles:
                prompt_parts.append(f"Topics discussed: {', '.join(topic_titles)}")
            prompt_parts.append(
                "\nBased on the above, generate a concise 5-8 word title that captures "
                "what this meeting was about. Return ONLY the title, nothing else."
            )
            prompt = "\n".join(prompt_parts)

            try:
                title = query_ollama(prompt, config).strip().strip('"\'')
                if title:
                    repo.update_title(meeting["id"], title)
                    updated += 1
                    log.info("Backfilled title for meeting %d: %s", meeting["id"], title)
            except Exception:
                log.warning("Failed to generate title for meeting %d", meeting["id"], exc_info=True)

        return {"updated": updated, "total_without_title": len(meetings)}

    return router
