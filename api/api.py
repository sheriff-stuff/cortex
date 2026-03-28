"""REST API layer over the meeting notes pipeline."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
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
