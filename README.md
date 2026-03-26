# Meeting Notes CLI

A local AI tool that takes recorded meeting files and produces structured Markdown notes with speaker-labeled transcripts, topic summaries, decisions, action items, and matched Q&A — all running entirely on your machine.

## Features

- Transcribes audio/video with speaker diarization (Speaker 1, Speaker 2, etc.)
- Extracts key topics, decisions, action items, and questions with answers
- Flags audio quality issues (low confidence, overlapping speech, silence gaps)
- Outputs clean Markdown with YAML frontmatter
- Persistent database storage (SQLite locally, PostgreSQL for production)
- Everything runs locally — no cloud services, no data leaves your machine

## Requirements

- Python 3.10+
- [Node.js](https://nodejs.org/) 18+ (for the web frontend)
- NVIDIA GPU with CUDA (recommended, CPU fallback available)
- [ffmpeg](https://ffmpeg.org/) installed (includes `ffprobe`, both must be on your PATH)
- [Ollama](https://ollama.ai/) installed and running
- HuggingFace account with access to [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)

## Quick Start

The fastest way to get the full app (backend + frontend) running:

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

## Installation (CLI only)

If you only need the CLI tool (no web UI):

```bash
# Install PyTorch with CUDA (adjust cu128 to your CUDA version)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128

# Install the tool
pip install -e .

# Login to HuggingFace (required for speaker diarization model)
huggingface-cli login

# Pull the Ollama model
ollama pull qwen2.5-coder:32b
```

## Usage

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

### API Server

The tool also includes a REST API for use with a web frontend:

```bash
# Install API dependencies
pip install -e ".[api]"

# Start the API server (default: http://127.0.0.1:9000)
meeting-notes serve

# Custom host/port
meeting-notes serve --host 0.0.0.0 --port 3001

# Connect to an external PostgreSQL database
meeting-notes serve --database-url "postgresql://user:pass@host/db"
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/jobs` | Upload audio/video file, returns job ID |
| `GET` | `/jobs/{id}` | Get job status and progress |
| `GET` | `/jobs/{id}/notes` | Get completed meeting notes (markdown) |
| `GET` | `/jobs/{id}/events` | SSE stream of real-time progress updates |
| `GET` | `/api/notes` | List all saved meeting notes |
| `GET` | `/api/notes/{filename}` | Get parsed meeting notes as JSON |

### Supported Formats

- **Audio**: MP3, WAV, M4A, AAC
- **Video**: MP4, MKV, AVI, MOV

## Configuration

Create `~/.config/meeting-notes/config.yaml` to set defaults:

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

CLI flags override config file values.

## Example Output

The tool generates a Markdown file with:

- **YAML frontmatter** — date, duration, speakers, source file, models used, quality flags
- **JSON sidecar** — companion `.json` file with full structured data (used by the API)
- **Key Topics Discussed** — main subjects with descriptions
- **Decisions Made** — what was decided, by whom, when
- **Action Items** — tasks with assignees and deadlines
- **Questions & Answers** — questions matched with answers (or flagged as unanswered)
- **Full Transcript** — speaker-labeled with timestamps
- **Quality Notes** — flagged audio issues

## Development

### Using `start-dev.sh` (recommended)

The dev script installs dependencies, starts Ollama, the backend (with hot-reload), and the frontend in one command:

```bash
bash start-dev.sh
```

- Frontend (Vite): http://localhost:5173
- Backend (FastAPI): http://127.0.0.1:9000
- Press Ctrl+C to stop everything

### Manual setup

```bash
# Backend
pip install -e ".[api]"
meeting-notes serve --reload          # http://127.0.0.1:9000

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

The Vite dev server proxies `/api/*` and `/jobs/*` requests to the backend at port 9000.

### Frontend

The web UI is a React + Vite + TypeScript app in `frontend/`.

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server at http://localhost:5173 |
| `npm run build` | Production build (outputs to `frontend/dist/`) |
| `npm run lint` | Run ESLint |

### Windows notes

When running Python commands directly (outside of `meeting-notes` CLI), set the UTF-8 flag:

```bash
PYTHONUTF8=1 python -X utf8 your_script.py
```

## How It Works

1. **Audio extraction** — extracts audio from video via ffmpeg (or uses audio directly)
2. **Transcription** — WhisperX with large-v3 model for speech-to-text with word-level timestamps
3. **Speaker diarization** — pyannote identifies and labels different speakers
4. **Quality analysis** — flags low confidence regions, overlapping speech, and silence gaps
5. **LLM extraction** — transcript is chunked and sent to Ollama for structured extraction
6. **Deduplication** — results from overlapping chunks are merged and deduplicated
7. **Markdown output** — everything rendered into a structured Markdown file
8. **JSON sidecar** — structured extraction data saved alongside the Markdown for direct API consumption
