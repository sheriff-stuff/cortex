"""REST API layer over the meeting notes pipeline."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.config import Config, load_config
from api.db import MeetingRepository, create_db_engine, init_db
from api.routes.jobs import create_router as jobs_router
from api.routes.notes import create_router as notes_router
from api.routes.templates import create_router as templates_router


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

    app.include_router(jobs_router(config, repo))
    app.include_router(notes_router(repo))
    app.include_router(templates_router(config, repo))

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

    llm_provider = os.environ.get("MEETING_NOTES_LLM_PROVIDER")
    llm_api_key = os.environ.get("MEETING_NOTES_LLM_API_KEY")
    llm_base_url = os.environ.get("MEETING_NOTES_LLM_BASE_URL")

    cli_overrides = {}
    if database_url:
        cli_overrides["database_url"] = database_url
    if llm_provider:
        cli_overrides["llm_provider"] = llm_provider
    if llm_api_key:
        cli_overrides["llm_api_key"] = llm_api_key
    if llm_base_url:
        cli_overrides["llm_base_url"] = llm_base_url

    config = load_config(
        config_path=Path(config_path) if config_path else None,
        cli_overrides=cli_overrides,
    )
    return create_app(config)
