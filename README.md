# Meeting Notes

A local AI meeting notes app that takes recorded meeting files and produces structured notes with speaker-labeled transcripts, topic summaries, decisions, action items, and matched Q&A. Includes a web UI and REST API. Everything runs on your machine — no cloud services, no data leaves your network.

## Features

- **Transcription with speaker diarization** — WhisperX + pyannote identifies who said what
- **Structured extraction** — LLM pulls out topics, decisions, action items, and Q&A
- **Audio quality analysis** — flags low confidence, overlapping speech, and silence gaps
- **Custom templates** — write your own extraction prompts to control what gets extracted
- **Speaker name editing** — rename "Speaker 1" to real names after processing
- **Re-summarize** — re-run extraction with a different template without re-transcribing
- **Two-phase pipeline** — transcription and summary run independently; transcript survives if LLM is down
- **Web UI** — React frontend for uploading, viewing, and managing meeting notes
- **Persistent storage** — SQLite locally, PostgreSQL for production
- **Fully local** — Ollama for LLM, WhisperX for transcription, pyannote for diarization

## Requirements

- Python 3.10+
- [Node.js](https://nodejs.org/) 18+ (for the web frontend)
- NVIDIA GPU with CUDA (recommended, CPU fallback available)
- [ffmpeg](https://ffmpeg.org/) installed and on your PATH
- [Ollama](https://ollama.ai/) installed and running
- HuggingFace account with access to [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)

## Quick Start

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate          # Windows

# 2. Install PyTorch with CUDA (adjust cu128 to your CUDA version)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128

# 3. Install the backend with API dependencies
pip install -e ".[api]"

# 4. Login to HuggingFace (required for speaker diarization)
huggingface-cli login

# 5. Pull the Ollama model
ollama pull qwen2.5-coder:32b

# 6. Install frontend dependencies
cd frontend && npm install && cd ..

# 7. Start everything (backend + frontend + Ollama)
bash start-dev.sh
```

Open **http://localhost:5173** for the web UI. The API runs at http://127.0.0.1:9000.

### CLI Only (no web UI)

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -e .
huggingface-cli login
ollama pull qwen2.5-coder:32b
```

## Usage

### Web UI

Upload a recording through the web interface at http://localhost:5173. You can:
- Select a custom extraction template before uploading
- Watch real-time progress via SSE events
- View structured notes with topics, decisions, action items, and Q&A
- Rename speakers to real names
- Re-summarize with a different template

### CLI

```bash
# Process a meeting recording
meeting-notes process recording.mp4

# Specify output directory
meeting-notes process recording.mp4 -o ~/meeting-notes/

# Transcript only (skip LLM extraction)
meeting-notes process recording.mp4 --no-llm

# Use a different Whisper model
meeting-notes process recording.mp4 --whisper-model medium

# Use a different Ollama model
meeting-notes process recording.mp4 --llm-model llama3:8b
```

### Supported Formats

- **Audio**: MP3, WAV, M4A, AAC
- **Video**: MP4, MKV, AVI, MOV

## Configuration

Create `~/.config/meeting-notes/config.yaml`:

```yaml
whisper_model: "large-v3"
whisper_device: "cuda"
whisper_compute_type: "float16"
llm_model: "qwen2.5-coder:32b"
ollama_url: "http://localhost:11434"
default_output_dir: "./meeting-notes"
chunk_max_tokens: 3000
chunk_overlap_seconds: 120
hf_token: ""
database_url: "sqlite:///meeting-notes.db"
```

CLI flags override config file values, which override defaults.

## API Server

```bash
meeting-notes serve                    # http://127.0.0.1:9000
meeting-notes serve --reload           # dev mode with hot-reload
meeting-notes serve --host 0.0.0.0 --port 3001
meeting-notes serve --database-url "postgresql://user:pass@host/db"
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/jobs` | Upload audio/video file, start processing |
| `GET` | `/jobs` | List active (queued/processing) jobs |
| `GET` | `/jobs/{id}` | Job status and progress |
| `GET` | `/jobs/{id}/notes` | Completed meeting notes (markdown) |
| `GET` | `/jobs/{id}/events` | SSE stream of real-time progress |
| `POST` | `/jobs/{id}/resummarize` | Re-run extraction with a different template |
| `GET` | `/api/notes` | List all saved meeting notes |
| `GET` | `/api/notes/{filename}` | Parsed meeting notes as JSON |
| `GET` | `/api/notes/{filename}/speakers` | Speaker name mappings |
| `PUT` | `/api/notes/{filename}/speakers` | Update speaker names |
| `GET` | `/api/templates` | List all templates |
| `GET` | `/api/templates/{id}` | Get template with prompt text |
| `POST` | `/api/templates` | Create a new template |
| `PUT` | `/api/templates/{id}` | Update a template |
| `DELETE` | `/api/templates/{id}` | Delete a template |
| `POST` | `/api/templates/{id}/duplicate` | Duplicate a template |
| `POST` | `/api/templates/render-example` | Preview extraction with example transcript |

## Development

### Using `start-dev.sh` (recommended)

```bash
bash start-dev.sh
```

Starts Ollama, the backend (with hot-reload), and the frontend dev server. Press Ctrl+C to stop.

- Frontend (Vite): http://localhost:5173
- Backend (FastAPI): http://127.0.0.1:9000

### Manual setup

```bash
# Backend (terminal 1)
pip install -e ".[api]"
meeting-notes serve --reload

# Frontend (terminal 2)
cd frontend && npm install && npm run dev
```

The Vite dev server proxies `/api/*` and `/jobs/*` to the backend at port 9000.

### Windows notes

When running Python directly (outside of `meeting-notes` CLI), set the UTF-8 flag:

```bash
PYTHONUTF8=1 python -X utf8 your_script.py
```

## Project Structure

```
api/
  api.py          FastAPI endpoints and app factory
  server.py       uvicorn entry point (click CLI)
  db.py           SQLAlchemy Core database layer
  jobs.py         Job model, in-memory store, pipeline runner
  config.py       Config dataclass (defaults < YAML < CLI flags)
  audio.py        Format validation, ffmpeg audio extraction
  transcribe.py   WhisperX transcription + diarization assembly
  diarize.py      pyannote speaker diarization
  extractor.py    LLM response parsing, chunk merging, deduplication
  llm.py          Ollama HTTP client and transcript chunking
  prompts.py      Extraction schema and prompt templates
  markdown.py     Markdown + JSON sidecar rendering
  quality.py      Audio quality analysis (confidence, overlap, silence)
  pipeline.py     CLI single-pass pipeline orchestrator
  cli.py          Click CLI entry points

frontend/
  src/
    App.tsx         Main app with routing
    api.ts          API client functions
    types.ts        TypeScript type definitions
    components/     React components (upload, notes list, notes view, etc.)
    components/ui/  shadcn/ui primitives
```

## How It Works

```
                          Meeting Notes Pipeline
                          ======================

  Audio/Video File
        |
        v
  +--------------+
  | Audio        |  ffmpeg extracts audio from video, converts to
  | Extraction   |  16kHz mono WAV for Whisper
  +--------------+
        |
        v
  +--------------+
  | Transcription|  WhisperX (large-v3) converts speech to text
  | (WhisperX)   |  with word-level timestamps and confidence scores
  +--------------+
        |
        v
  +--------------+
  | Speaker      |  pyannote identifies different voices and labels
  | Diarization  |  each segment (Speaker 1, Speaker 2, etc.)
  +--------------+
        |
        v
  +--------------+
  | Quality      |  Flags low-confidence regions, overlapping speech,
  | Analysis     |  and silence gaps > 10 seconds
  +--------------+
        |
        |  Phase 1 complete — transcript saved to DB
        |  (Phase 2 fails gracefully if Ollama is down)
        v
  +--------------+
  | Chunking     |  Splits transcript into chunks under token limit
  |              |  with time-based overlap to capture Q&A at boundaries
  +--------------+
        |
        v
  +--------------+
  | LLM          |  Each chunk sent to Ollama for structured extraction
  | Extraction   |  (topics, decisions, action items, questions, keywords)
  +--------------+
        |
        v
  +--------------+
  | Merge &      |  Results from overlapping chunks are merged;
  | Deduplicate  |  near-duplicate items removed by text similarity
  +--------------+
        |
        v
  Structured Notes (Markdown + JSON + Database)
```

### What Does Diarization Look Like?

Diarization is the process of figuring out **who is speaking when**. Without it, you just get a wall of text. With it, you get a conversation:

```
WITHOUT diarization (raw transcript):
======================================
[00:00:15] Alright, let's get started. Thanks for joining today.
[00:00:23] Sounds good. I've been looking at both PostgreSQL and MySQL.
[00:00:32] Agreed. We're also storing a lot of unstructured data.
[00:00:40] Okay, so leaning toward Postgres. Any concerns?
[00:00:45] No major concerns. Our team has more experience with Postgres.


WITH diarization (speaker-labeled transcript):
===============================================
[00:00:15] Speaker 1: Alright, let's get started. Thanks for joining today.
[00:00:23] Speaker 2: Sounds good. I've been looking at both PostgreSQL and MySQL.
[00:00:32] Speaker 3: Agreed. We're also storing a lot of unstructured data.
[00:00:40] Speaker 1: Okay, so leaning toward Postgres. Any concerns?
[00:00:45] Speaker 2: No major concerns. Our team has more experience with Postgres.
```

The diarization model (pyannote) analyzes the audio waveform to detect voice characteristics — pitch, timbre, cadence — and groups segments by speaker. It doesn't know names, just that "this voice" is different from "that voice." You can assign real names in the web UI after processing.
