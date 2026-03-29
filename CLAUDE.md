# CLAUDE.md

## Project

Local AI meeting notes app with React frontend and FastAPI backend. Transcribes recordings with speaker diarization, extracts structured notes via LLM. Python 3.10+, api/ layout.

## Commands

- `pip install -e ".[api]"` — install with API deps
- `meeting-notes serve` — start the API server (default `127.0.0.1:9000`)
- `meeting-notes serve --reload` — dev mode with hot-reload (WatchFiles); do NOT kill/restart after code changes
- `meeting-notes serve --database-url "postgresql://user:pass@host/db"` — connect to external database
- `PYTHONUTF8=1 python -X utf8` — required on Windows for direct python invocations

## Gotchas

- WhisperX 3.8 changed APIs: `DiarizationPipeline` lives at `whisperx.diarize`, not top-level `whisperx`. Uses `token=` not `use_auth_token=`.
- pyannote model is gated — requires HuggingFace token + accepting terms at huggingface.co/pyannote/speaker-diarization-community-1
- `ffprobe` path: don't derive from ffmpeg path with string replace — use `shutil.which("ffprobe")` (Windows paths break naive replacement)
- torch/torchvision/torchaudio must be installed together with CUDA index (`pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128`), pip defaults to CPU-only. Mismatched versions cause circular import errors in torchvision.
- torchcodec warnings on Windows are harmless — pyannote falls back to ffmpeg for audio loading
- Ollama model default is `qwen2.5-coder:32b` (not `qwen2.5:32b` which isn't pulled locally)
- In-memory SQLite (`sqlite:///:memory:`) requires `StaticPool` — already configured in `create_db_engine()`.
- No inline migration code in `db.py`: when schema changes are made, update `migration/SCHEMA.md` to match and run `python migration/migrate.py` to bring the live DB up to date. Never delete user data.
- The `🤖 *beep boop — this is Claude, not a human*` prefix on GitHub comments is load-bearing — the `/review-pr` polling loop uses it to identify bot replies and determine which threads are unresolved. Don't change or remove this prefix without updating the detection logic in `review-pr.md`.

## Architecture

Two-phase pipeline in `jobs.py`: **Phase 1 (transcription)**: `audio.py` → `transcribe.py` → `quality.py` → save transcript to DB. **Phase 2 (summary)**: load transcript from `transcript_segments` table → `extractor.py`/`llm.py` → update meeting with extraction results. Phase 2 auto-chains after Phase 1 but fails gracefully (transcript survives if Ollama is down). `POST /jobs/{job_id}/resummarize` re-runs Phase 2 with a different template. CLI pipeline in `pipeline.py` still runs as a single pass. Pipeline outputs both `.md` (human-readable) and `.json` sidecar (structured data). After processing, structured data is saved directly to the database from the extraction results (not from parsing markdown). API layer: `api.py` (app factory + router wiring), `routes/jobs.py` (job endpoints), `routes/notes.py` (notes + speaker endpoints), `routes/templates.py` (template endpoints), `responses.py` (formatting helpers), `server.py` (uvicorn entry point), and `db.py` (SQLAlchemy Core database layer). Data is stored in a database (SQLite by default, configurable for PostgreSQL). API reads exclusively from DB. All in `api/`, with `routes/` sub-package for endpoint modules. Config is a dataclass in `config.py` (defaults < YAML file < CLI flags). No Pydantic. Frontend is React + Vite + TypeScript in `frontend/`.

Custom templates are instructions only — no placeholders needed. `build_extraction_prompt()` in `prompts.py` assembles the final prompt: transcript + schema + instructions.

## Frontend

React 19 + Vite 8 + TypeScript (strict) in `frontend/`. Tailwind CSS v4 + shadcn/ui for styling. Components in `src/components/`, shadcn primitives in `src/components/ui/`. API client in `src/api.ts`, types in `src/types.ts`. Uses `@/` path alias. Vite proxies `/api/*` and `/jobs/*` to `localhost:9000`.
