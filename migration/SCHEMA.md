# Database Schema

Source of truth: `api/db.py` (SQLAlchemy Core table definitions).

When the schema in `db.py` changes, compare this document against the new table definitions to understand what columns were added, removed, or modified — then write a migration script.

## Tables

### jobs
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | VARCHAR(12) | NO | — | Primary key |
| status | VARCHAR(20) | NO | "queued" | queued/running/done/error |
| progress | TEXT | NO | "" | Human-readable progress message |
| notes_markdown | TEXT | YES | — | Final markdown output |
| error | TEXT | YES | — | Error message if failed |
| source_filename | VARCHAR(255) | NO | — | Original upload filename |
| template_id | INTEGER | YES | — | FK to templates.id |
| phase | VARCHAR(20) | YES | — | Current pipeline phase |
| meeting_id | INTEGER | YES | — | FK to meetings.id |
| created_at | VARCHAR(30) | NO | — | ISO 8601 timestamp |
| updated_at | VARCHAR(30) | NO | — | ISO 8601 timestamp |

### meetings
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | INTEGER | NO | auto | Primary key, autoincrement |
| filename | VARCHAR(255) | NO | — | Unique |
| job_id | VARCHAR(12) | YES | — | FK to jobs.id |
| meeting_date | VARCHAR(10) | YES | — | YYYY-MM-DD |
| meeting_time | VARCHAR(5) | YES | — | HH:MM |
| duration | VARCHAR(20) | YES | — | Human-readable duration |
| speakers | INTEGER | YES | — | Speaker count |
| audio_file | TEXT | YES | — | Path to audio file |
| processing_date | VARCHAR(30) | YES | — | ISO 8601 timestamp |
| whisper_model | VARCHAR(50) | YES | — | Model used for transcription |
| llm_model | VARCHAR(100) | YES | — | Model used for extraction |
| quality_flags | TEXT | YES | — | JSON string |
| markdown_content | TEXT | YES | — | Full markdown output |
| topic_count | INTEGER | YES | 0 | |
| decision_count | INTEGER | YES | 0 | |
| action_item_count | INTEGER | YES | 0 | |
| question_count | INTEGER | YES | 0 | |
| overview | TEXT | YES | — | Meeting overview/summary text |
| keywords | TEXT | YES | — | JSON string of keyword list |
| created_at | VARCHAR(30) | NO | — | ISO 8601 timestamp |

### meeting_items
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | INTEGER | NO | auto | Primary key, autoincrement |
| meeting_id | INTEGER | NO | — | FK to meetings.id |
| item_type | VARCHAR(20) | NO | — | topic/decision/action_item/question |
| data | TEXT | NO | — | JSON string |
| sort_order | INTEGER | NO | 0 | |

Indexes: `ix_meeting_items_meeting_type` on (meeting_id, item_type)

### speaker_names
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | INTEGER | NO | auto | Primary key, autoincrement |
| meeting_id | INTEGER | NO | — | FK to meetings.id |
| label | VARCHAR(50) | NO | — | "Speaker 1", etc. |
| name | VARCHAR(255) | NO | — | User-assigned name |

Constraints: unique (meeting_id, label)
Indexes: `ix_speaker_names_meeting` on (meeting_id)

### transcript_segments
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | INTEGER | NO | auto | Primary key, autoincrement |
| meeting_id | INTEGER | NO | — | FK to meetings.id |
| sort_order | INTEGER | NO | — | |
| start_time | FLOAT | NO | — | Seconds |
| end_time | FLOAT | NO | — | Seconds |
| speaker | VARCHAR(100) | NO | — | Speaker label |
| text | TEXT | NO | — | Segment text |
| confidence | FLOAT | NO | 1.0 | Transcription confidence |

Indexes: `ix_transcript_segments_meeting` on (meeting_id)

### templates
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | INTEGER | NO | auto | Primary key, autoincrement |
| name | VARCHAR(255) | NO | — | Template name |
| description | TEXT | NO | "" | |
| prompt_text | TEXT | NO | — | Extraction instructions |
| is_default | INTEGER | NO | 0 | 1 = default template |
| created_at | VARCHAR(30) | NO | — | ISO 8601 timestamp |
| updated_at | VARCHAR(30) | NO | — | ISO 8601 timestamp |
