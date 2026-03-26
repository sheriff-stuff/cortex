"""Database layer: schema definition and repository (SQLAlchemy Core)."""

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
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
    Column("created_at", String(30), nullable=False),
    Column("updated_at", String(30), nullable=False),
)

meetings_table = Table(
    "meetings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("filename", String(255), unique=True, nullable=False),
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
    Column("created_at", String(30), nullable=False),
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MeetingRepository:
    """All database operations for jobs and meetings."""

    def __init__(self, engine: Engine):
        self._engine = engine

    # --- Job CRUD ---

    def create_job(self, job_id: str, source_filename: str) -> None:
        now = _now_iso()
        with self._engine.begin() as conn:
            conn.execute(
                insert(jobs_table).values(
                    id=job_id,
                    status="queued",
                    progress="Waiting to start",
                    source_filename=source_filename,
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
                    created_at=now,
                )
            )
            meeting_id = result.inserted_primary_key[0]

            # Insert items for each type
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
        """Return summary dicts matching the GET /api/notes response shape."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    meetings_table.c.filename,
                    meetings_table.c.meeting_date,
                    meetings_table.c.meeting_time,
                    meetings_table.c.duration,
                    meetings_table.c.speakers,
                    meetings_table.c.topic_count,
                    meetings_table.c.action_item_count,
                )
                .order_by(meetings_table.c.filename.desc())
            ).mappings().all()
            return [dict(r) for r in rows]

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

            # Reconstruct sidecar-shaped dict
            quality_flags = None
            if row["quality_flags"]:
                quality_flags = json.loads(row["quality_flags"])

            meeting_meta = {
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
                meeting_meta["quality_flags"] = quality_flags

            # Load items grouped by type
            items_by_type: dict[str, list[dict]] = {
                "topics": [],
                "decisions": [],
                "action_items": [],
                "questions": [],
            }
            item_rows = conn.execute(
                select(meeting_items_table.c.item_type, meeting_items_table.c.data)
                .where(meeting_items_table.c.meeting_id == row["id"])
                .order_by(
                    meeting_items_table.c.item_type,
                    meeting_items_table.c.sort_order,
                )
            ).all()
            for item_row in item_rows:
                item_type = item_row[0]
                if item_type in items_by_type:
                    items_by_type[item_type].append(json.loads(item_row[1]))

            return {
                "filename": row["filename"],
                "metadata": meeting_meta,
                "summary": {
                    "topic_count": row["topic_count"],
                    "decision_count": row["decision_count"],
                    "action_item_count": row["action_item_count"],
                    "question_count": row["question_count"],
                },
                "markdown_content": row["markdown_content"],
                **items_by_type,
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
    """Create all tables if they don't exist."""
    metadata.create_all(engine)
