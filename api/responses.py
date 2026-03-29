"""Response formatting helpers for the meeting notes API."""

from fastapi import HTTPException

from api.jobs import Job


def format_detail(*parts: str) -> str:
    """Join non-empty parts with ', '. Returns '' if all parts are empty."""
    return ", ".join(p for p in parts if p)


def format_action_detail(item: dict) -> str:
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


def transform_items(topics: list, decisions: list, action_items: list, questions: list) -> dict:
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
            {"decision": d.get("decision", ""), "detail": format_detail(d.get("speaker", ""), d.get("timestamp", ""))}
            for d in decisions
        ],
        "action_items": [
            {"task": a.get("task", ""), "detail": format_action_detail(a)}
            for a in action_items
        ],
        "questions": [
            {
                "question": q.get("question", ""),
                "attribution": format_detail(q.get("asker", ""), q.get("timestamp", "")),
                "answer": q.get("answer") or None,
                "answer_attribution": format_detail(q.get("answerer", ""), q.get("answer_timestamp", "")) or None,
            }
            for q in questions
        ],
    }


def response_from_sidecar(sidecar: dict, filename: str) -> dict:
    """Transform a sidecar dict into the API contract shape."""
    result = transform_items(
        sidecar.get("topics", []),
        sidecar.get("decisions", []),
        sidecar.get("action_items", []),
        sidecar.get("questions", []),
    )
    result["filename"] = filename
    result["title"] = sidecar.get("title", "")
    result["job_id"] = sidecar.get("job_id")
    result["metadata"] = sidecar["metadata"]
    result["summary"] = sidecar["summary"]
    result["overview"] = sidecar.get("overview", "")
    result["keywords"] = sidecar.get("keywords", [])
    return result


def job_status_dict(source) -> dict:
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


def check_filename(filename: str) -> None:
    """Raise 400 if filename looks like a path traversal."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
