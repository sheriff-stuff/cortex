"""Notes and speaker API routes."""

from fastapi import APIRouter, HTTPException

from api.db import MeetingRepository
from api.responses import check_filename, parse_transcript, response_from_sidecar


def create_router(repo: MeetingRepository) -> APIRouter:
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
        result["transcript"] = parse_transcript(db_meeting.get("markdown_content"))
        meeting_id = repo.get_meeting_id_by_filename(filename)
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

    return router
