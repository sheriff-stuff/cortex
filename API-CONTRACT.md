# API Contract

Single source of truth for all API endpoints and response shapes.

## `POST /jobs`
- **Request**: `multipart/form-data` with field `file` (audio/video file)
- **Accepted formats**: `.mp3, .wav, .m4a, .aac, .mp4, .mkv, .avi, .mov`
- **Response** (202): `{ "job_id": string, "status": "queued" }`
- **Errors**: 400 if no filename or unsupported format

## `GET /jobs/{job_id}`
- **Response** (200): `{ "job_id": string, "status": "queued"|"processing"|"completed"|"failed", "progress": string, "source_filename": string, "error"?: string }`
- **Errors**: 404 if job not found

## `GET /jobs/{job_id}/notes`
- **Response** (200): `{ "job_id": string, "markdown": string }`
- **Errors**: 404 (not found), 409 (not yet completed), 422 (job failed)

## `GET /jobs/{job_id}/events` (SSE)
- **Event types**: `status`, `progress`, `ping`, `done`
- **Data**: string (progress message or status value)

## `GET /api/notes`
- **Response** (200): array of `{ "filename": string, "meeting_date": string, "meeting_time": string, "duration": string, "speakers": number, "topic_count": number, "action_item_count": number }`
- **Source**: database (populated during pipeline processing)

## `GET /api/notes/{filename}`
- **Response** (200): `{ "filename": string, "metadata": object, "summary": { "topic_count": number, "decision_count": number, "action_item_count": number, "question_count": number }, "topics": [{ "title": string, "description": string }], "decisions": [{ "decision": string, "detail": string }], "action_items": [{ "task": string, "detail": string }], "questions": [{ "question": string, "attribution": string }] }`
- **Errors**: 400 (path traversal), 404 (not found), 500 (parse failure)
- **Security**: rejects filenames containing `/`, `\`, or `..`. Resolves path and checks `is_relative_to` output dir.
- **Speaker names**: response also includes `"speaker_names": { "Speaker 1": "Alice", ... }` (empty `{}` if none assigned)

## `GET /api/notes/{filename}/speakers`
- **Response** (200): `{ "speaker_names": { "Speaker 1": "Alice", "Speaker 2": "Bob" } }`
- **No names assigned**: `{ "speaker_names": {} }`
- **Errors**: 400 (path traversal), 404 (meeting not found)

## `PUT /api/notes/{filename}/speakers`
- **Request body**: `{ "speaker_names": { "Speaker 1": "Alice", "Speaker 2": "Bob" } }`
- **Response** (200): `{ "speaker_names": { "Speaker 1": "Alice", "Speaker 2": "Bob" } }`
- **Semantics**: Idempotent. Replaces all speaker names for this meeting. Sending `{}` clears all names. Empty-string values are filtered out.
- **Errors**: 400 (path traversal / invalid body), 404 (meeting not found)
