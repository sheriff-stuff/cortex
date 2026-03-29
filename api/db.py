"""Database layer: schema definition and repository (SQLAlchemy Core)."""

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

metadata = MetaData()

jobs_table = Table(
    "jobs",
    metadata,
    Column("id", String(12), primary_key=True),
    Column("status", String(20), nullable=False, default="queued"),
    Column("progress", Text, nullable=False, default=""),
    Column("notes_markdown", Text, nullable=True),
    Column("error", Text, nullable=True),
    Column("source_filename", String(255), nullable=False),
    Column("template_id", Integer, nullable=True),
    Column("phase", String(20), nullable=True),
    Column("meeting_id", Integer, nullable=True),
    Column("created_at", String(30), nullable=False),
    Column("updated_at", String(30), nullable=False),
)

meetings_table = Table(
    "meetings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("filename", String(255), unique=True, nullable=False),
    Column("title", String(500), nullable=True),
    Column("job_id", String(12), nullable=True),
    Column("meeting_date", String(10)),
    Column("meeting_time", String(5)),
    Column("duration", String(20)),
    Column("speakers", Integer),
    Column("audio_file", Text),
    Column("processing_date", String(30)),
    Column("whisper_model", String(50)),
    Column("llm_model", String(100)),
    Column("quality_flags", Text),  # JSON string
    Column("markdown_content", Text),
    Column("topic_count", Integer, default=0),
    Column("decision_count", Integer, default=0),
    Column("action_item_count", Integer, default=0),
    Column("question_count", Integer, default=0),
    Column("overview", Text, nullable=True),
    Column("keywords", Text, nullable=True),  # JSON string
    Column("created_at", String(30), nullable=False),
    Column("updated_at", String(30), nullable=False),
)

meeting_items_table = Table(
    "meeting_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("meeting_id", Integer, nullable=False),
    Column("item_type", String(20), nullable=False),
    Column("data", Text, nullable=False),  # JSON string
    Column("sort_order", Integer, nullable=False, default=0),
    Index("ix_meeting_items_meeting_type", "meeting_id", "item_type"),
)

speaker_names_table = Table(
    "speaker_names",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("meeting_id", Integer, nullable=False),
    Column("label", String(50), nullable=False),   # "Speaker 1", "Speaker 2", etc.
    Column("name", String(255), nullable=False),    # User-assigned name
    UniqueConstraint("meeting_id", "label", name="uq_speaker_names_meeting_label"),
    Index("ix_speaker_names_meeting", "meeting_id"),
)

transcript_segments_table = Table(
    "transcript_segments",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("meeting_id", Integer, nullable=False),
    Column("sort_order", Integer, nullable=False),
    Column("start_time", Float, nullable=False),
    Column("end_time", Float, nullable=False),
    Column("speaker", String(100), nullable=False),
    Column("text", Text, nullable=False),
    Column("confidence", Float, nullable=False, default=1.0),
    Index("ix_transcript_segments_meeting", "meeting_id"),
)

templates_table = Table(
    "templates",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("prompt_text", Text, nullable=False),
    Column("is_default", Integer, nullable=False, default=0),
    Column("created_at", String(30), nullable=False),
    Column("updated_at", String(30), nullable=False),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MeetingRepository:
    """All database operations for jobs and meetings."""

    def __init__(self, engine: Engine):
        self._engine = engine

    @staticmethod
    def _insert_meeting_items(conn, meeting_id: int, sidecar: dict) -> None:
        """Insert meeting items (topics, decisions, etc.) within an existing transaction."""
        for item_type in ("topics", "decisions", "action_items", "questions"):
            items = sidecar.get(item_type, [])
            for i, item in enumerate(items):
                conn.execute(
                    insert(meeting_items_table).values(
                        meeting_id=meeting_id,
                        item_type=item_type,
                        data=json.dumps(item, ensure_ascii=False),
                        sort_order=i,
                    )
                )

    # --- Job CRUD ---

    def create_job(
        self, job_id: str, source_filename: str, template_id: int | None = None,
    ) -> None:
        now = _now_iso()
        with self._engine.begin() as conn:
            conn.execute(
                insert(jobs_table).values(
                    id=job_id,
                    status="queued",
                    progress="Waiting to start",
                    source_filename=source_filename,
                    template_id=template_id,
                    created_at=now,
                    updated_at=now,
                )
            )

    def get_job(self, job_id: str) -> dict | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(jobs_table).where(jobs_table.c.id == job_id)
            ).mappings().first()
            if row is None:
                return None
            return dict(row)

    def update_job(self, job_id: str, **fields: object) -> None:
        fields["updated_at"] = _now_iso()
        with self._engine.begin() as conn:
            conn.execute(
                update(jobs_table).where(jobs_table.c.id == job_id).values(**fields)
            )

    def fail_orphaned_jobs(self) -> int:
        """Mark queued/processing jobs as failed (server restart recovery)."""
        with self._engine.begin() as conn:
            result = conn.execute(
                update(jobs_table)
                .where(jobs_table.c.status.in_(["queued", "processing"]))
                .values(
                    status="failed",
                    error="Server restarted during processing",
                    updated_at=_now_iso(),
                )
            )
            return result.rowcount

    # --- Meeting CRUD ---

    def save_meeting(
        self, sidecar: dict, markdown_content: str, job_id: str | None = None,
    ) -> int:
        """Insert a meeting and its items. Returns the meeting id."""
        meta = sidecar.get("metadata", {})
        summary = sidecar.get("summary", {})
        quality = meta.get("quality_flags")
        now = _now_iso()

        with self._engine.begin() as conn:
            result = conn.execute(
                insert(meetings_table).values(
                    filename=sidecar.get("filename", ""),
                    title=sidecar.get("title", ""),
                    job_id=job_id,
                    meeting_date=meta.get("meeting_date", ""),
                    meeting_time=meta.get("meeting_time", ""),
                    duration=meta.get("duration", ""),
                    speakers=meta.get("speakers", 0),
                    audio_file=meta.get("audio_file", ""),
                    processing_date=meta.get("processing_date", ""),
                    whisper_model=meta.get("whisper_model", ""),
                    llm_model=meta.get("llm_model", ""),
                    quality_flags=json.dumps(quality) if quality else None,
                    markdown_content=markdown_content,
                    topic_count=summary.get("topic_count", 0),
                    decision_count=summary.get("decision_count", 0),
                    action_item_count=summary.get("action_item_count", 0),
                    question_count=summary.get("question_count", 0),
                    overview=sidecar.get("overview", ""),
                    keywords=json.dumps(sidecar.get("keywords", []), ensure_ascii=False),
                    created_at=now,
                    updated_at=now,
                )
            )
            meeting_id = result.inserted_primary_key[0]

            self._insert_meeting_items(conn, meeting_id, sidecar)

            return meeting_id

    def meeting_exists(self, filename: str) -> bool:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(meetings_table.c.id).where(
                    meetings_table.c.filename == filename
                )
            ).first()
            return row is not None

    def list_meetings(self) -> list[dict]:
        """Return summary dicts for GET /api/notes.

        Each dict contains: filename, title, meeting_date, meeting_time,
        duration, speakers, topic_count, action_item_count.
        The title may be empty for meetings created before the title feature.
        """
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    meetings_table.c.filename,
                    meetings_table.c.title,
                    meetings_table.c.meeting_date,
                    meetings_table.c.meeting_time,
                    meetings_table.c.duration,
                    meetings_table.c.speakers,
                    meetings_table.c.topic_count,
                    meetings_table.c.action_item_count,
                )
                .order_by(meetings_table.c.filename.desc())
            ).mappings().all()
            results = []
            for r in rows:
                d = dict(r)
                d["title"] = d.get("title") or ""
                results.append(d)
            return results

    @staticmethod
    def _build_meeting_meta(row: dict) -> dict:
        """Build metadata dict from a meeting DB row."""
        quality_flags = None
        if row["quality_flags"]:
            quality_flags = json.loads(row["quality_flags"])

        meta = {
            "meeting_date": row["meeting_date"],
            "meeting_time": row["meeting_time"],
            "duration": row["duration"],
            "speakers": row["speakers"],
            "audio_file": row["audio_file"],
            "processing_date": row["processing_date"],
            "whisper_model": row["whisper_model"],
            "llm_model": row["llm_model"],
        }
        if quality_flags:
            meta["quality_flags"] = quality_flags
        return meta

    @staticmethod
    def _load_meeting_items(conn, meeting_id: int) -> dict[str, list[dict]]:
        """Load meeting items grouped by type."""
        items_by_type: dict[str, list[dict]] = {
            "topics": [],
            "decisions": [],
            "action_items": [],
            "questions": [],
        }
        item_rows = conn.execute(
            select(meeting_items_table.c.item_type, meeting_items_table.c.data)
            .where(meeting_items_table.c.meeting_id == meeting_id)
            .order_by(
                meeting_items_table.c.item_type,
                meeting_items_table.c.sort_order,
            )
        ).all()
        for item_row in item_rows:
            item_type = item_row[0]
            if item_type in items_by_type:
                items_by_type[item_type].append(json.loads(item_row[1]))
        return items_by_type

    def get_meeting_by_filename(self, filename: str) -> dict | None:
        """Return a sidecar-shaped dict for a single meeting, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(
                select(meetings_table).where(
                    meetings_table.c.filename == filename
                )
            ).mappings().first()
            if row is None:
                return None
            row = dict(row)

            keywords = []
            if row.get("keywords"):
                try:
                    keywords = json.loads(row["keywords"])
                except (json.JSONDecodeError, TypeError):
                    pass

            return {
                "filename": row["filename"],
                "title": row.get("title") or "",
                "job_id": row.get("job_id"),
                "metadata": self._build_meeting_meta(row),
                "summary": {
                    "topic_count": row["topic_count"],
                    "decision_count": row["decision_count"],
                    "action_item_count": row["action_item_count"],
                    "question_count": row["question_count"],
                },
                "overview": row.get("overview") or "",
                "keywords": keywords,
                "markdown_content": row["markdown_content"],
                **self._load_meeting_items(conn, row["id"]),
            }

    # --- Speaker Names ---

    def get_meeting_id_by_filename(self, filename: str) -> int | None:
        """Return the meeting ID for a filename, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(
                select(meetings_table.c.id).where(
                    meetings_table.c.filename == filename
                )
            ).first()
            return row[0] if row else None

    def get_speaker_names(self, meeting_id: int) -> dict[str, str]:
        """Return speaker name mappings for a meeting. Empty dict if none."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    speaker_names_table.c.label,
                    speaker_names_table.c.name,
                ).where(speaker_names_table.c.meeting_id == meeting_id)
            ).all()
            return {row[0]: row[1] for row in rows}

    def save_speaker_names(self, meeting_id: int, names: dict[str, str]) -> None:
        """Replace all speaker names for a meeting. Filters out empty values."""
        with self._engine.begin() as conn:
            conn.execute(
                delete(speaker_names_table).where(
                    speaker_names_table.c.meeting_id == meeting_id
                )
            )
            for label, name in names.items():
                if name:  # skip empty strings
                    conn.execute(
                        insert(speaker_names_table).values(
                            meeting_id=meeting_id,
                            label=label,
                            name=name,
                        )
                    )

    # --- Transcript Segments ---

    def save_transcript_segments(self, meeting_id: int, segments: list) -> None:
        """Bulk-insert transcript segments for a meeting."""
        with self._engine.begin() as conn:
            for i, seg in enumerate(segments):
                conn.execute(
                    insert(transcript_segments_table).values(
                        meeting_id=meeting_id,
                        sort_order=i,
                        start_time=seg.start,
                        end_time=seg.end,
                        speaker=seg.speaker,
                        text=seg.text,
                        confidence=seg.confidence,
                    )
                )

    def get_transcript_segments(self, meeting_id: int) -> list:
        """Return transcript segments as Segment dataclass instances."""
        from api.transcribe import Segment

        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    transcript_segments_table.c.start_time,
                    transcript_segments_table.c.end_time,
                    transcript_segments_table.c.speaker,
                    transcript_segments_table.c.text,
                    transcript_segments_table.c.confidence,
                )
                .where(transcript_segments_table.c.meeting_id == meeting_id)
                .order_by(transcript_segments_table.c.sort_order)
            ).all()
            return [
                Segment(
                    start=row[0], end=row[1], speaker=row[2],
                    text=row[3], confidence=row[4],
                )
                for row in rows
            ]

    def get_meeting_id_by_job(self, job_id: str) -> int | None:
        """Return the meeting ID for a job, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(
                select(meetings_table.c.id).where(
                    meetings_table.c.job_id == job_id
                )
            ).first()
            return row[0] if row else None

    def update_meeting_extraction(
        self, meeting_id: int, sidecar: dict, markdown_content: str,
    ) -> None:
        """Update an existing meeting with LLM extraction results."""
        summary = sidecar.get("summary", {})
        meta = sidecar.get("metadata", {})

        with self._engine.begin() as conn:
            conn.execute(
                update(meetings_table)
                .where(meetings_table.c.id == meeting_id)
                .values(
                    title=sidecar.get("title", ""),
                    markdown_content=markdown_content,
                    llm_model=meta.get("llm_model", ""),
                    topic_count=summary.get("topic_count", 0),
                    decision_count=summary.get("decision_count", 0),
                    action_item_count=summary.get("action_item_count", 0),
                    question_count=summary.get("question_count", 0),
                    overview=sidecar.get("overview", ""),
                    keywords=json.dumps(sidecar.get("keywords", []), ensure_ascii=False),
                    updated_at=_now_iso(),
                )
            )
            # Replace meeting items
            conn.execute(
                delete(meeting_items_table).where(
                    meeting_items_table.c.meeting_id == meeting_id
                )
            )
            self._insert_meeting_items(conn, meeting_id, sidecar)

    def get_meeting_metadata_by_id(self, meeting_id: int) -> dict | None:
        """Return meeting row as dict by ID, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(
                select(meetings_table).where(meetings_table.c.id == meeting_id)
            ).mappings().first()
            if row is None:
                return None
            return dict(row)

    def get_meeting_markdown(self, filename: str) -> str | None:
        """Return just the markdown content for a meeting, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(
                select(meetings_table.c.markdown_content).where(
                    meetings_table.c.filename == filename
                )
            ).first()
            if row is None:
                return None
            return row[0]

    # --- Templates ---

    def list_templates(self) -> list[dict]:
        """Return all templates without prompt_text."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    templates_table.c.id,
                    templates_table.c.name,
                    templates_table.c.description,
                    templates_table.c.is_default,
                    templates_table.c.created_at,
                    templates_table.c.updated_at,
                ).order_by(templates_table.c.is_default.desc(), templates_table.c.id)
            ).mappings().all()
            return [dict(r) for r in rows]

    def get_template(self, template_id: int) -> dict | None:
        """Return a single template with prompt_text, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(
                select(templates_table).where(templates_table.c.id == template_id)
            ).mappings().first()
            if row is None:
                return None
            return dict(row)

    def create_template(self, name: str, description: str, prompt_text: str) -> int:
        """Create a new template. Returns the new ID."""
        now = _now_iso()
        with self._engine.begin() as conn:
            result = conn.execute(
                insert(templates_table).values(
                    name=name,
                    description=description,
                    prompt_text=prompt_text,
                    is_default=0,
                    created_at=now,
                    updated_at=now,
                )
            )
            return result.inserted_primary_key[0]

    def update_template(self, template_id: int, **fields: object) -> None:
        """Update a template's fields."""
        fields["updated_at"] = _now_iso()
        with self._engine.begin() as conn:
            conn.execute(
                update(templates_table)
                .where(templates_table.c.id == template_id)
                .values(**fields)
            )

    def delete_template(self, template_id: int) -> None:
        """Delete a template by ID."""
        with self._engine.begin() as conn:
            conn.execute(
                delete(templates_table).where(templates_table.c.id == template_id)
            )

    def duplicate_template(self, template_id: int) -> int | None:
        """Duplicate a template. Returns the new ID, or None if not found."""
        original = self.get_template(template_id)
        if original is None:
            return None
        return self.create_template(
            name=original["name"] + " (copy)",
            description=original["description"],
            prompt_text=original["prompt_text"],
        )


def create_db_engine(database_url: str) -> Engine:
    """Create engine with appropriate settings per dialect."""
    kwargs: dict = {}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        # In-memory SQLite needs StaticPool to share the DB across connections
        if ":memory:" in database_url:
            kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **kwargs)


def init_db(engine: Engine) -> None:
    """Create all tables if they don't exist, seed default template."""
    metadata.create_all(engine)
    _seed_default_template(engine)


def _seed_default_template(engine: Engine) -> None:
    """Insert or update the default extraction template."""
    from api.prompts import DEFAULT_INSTRUCTIONS

    now = _now_iso()
    with engine.connect() as conn:
        row = conn.execute(
            select(templates_table.c.id).where(templates_table.c.is_default == 1)
        ).first()

    if row is not None:
        with engine.begin() as conn:
            conn.execute(
                update(templates_table)
                .where(templates_table.c.id == row[0])
                .values(prompt_text=DEFAULT_INSTRUCTIONS, updated_at=now)
            )
        return

    with engine.begin() as conn:
        conn.execute(
            insert(templates_table).values(
                name="Default Extraction",
                description="Built-in extraction template that identifies topics, decisions, action items, and questions from meeting transcripts.",
                prompt_text=DEFAULT_INSTRUCTIONS,
                is_default=1,
                created_at=now,
                updated_at=now,
            )
        )
