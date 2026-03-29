# Setup Guide

Hey! Here's how to get this running on your PC.

## The Easy Way (Claude Code)

If you have [Claude Code](https://claude.ai/claude-code) installed, just open a terminal in this project folder and tell it:

> Set up this project on my PC using Docker. Walk me through creating my config file and getting everything running.

Claude Code will read the project files, figure out what you need, and walk you through each step. It can even edit your config file for you.

## The Manual Way

### Prerequisites

1. **Docker Desktop** — https://docs.docker.com/get-docker/
   - After installing, make sure Docker is running (check the system tray icon)
2. **HuggingFace account** — https://huggingface.co
   - Create a free account
   - Go to https://huggingface.co/pyannote/speaker-diarization-community-1 and accept the model terms (this is what identifies who's speaking)
   - Go to https://huggingface.co/settings/tokens and create a token — copy it somewhere safe

### Setup

```bash
# 1. Copy the config template
cp config.docker.yaml config.yaml
```

Open `config.yaml` in any text editor and paste your HuggingFace token into the `hf_token` line:
```yaml
hf_token: "hf_your_token_here"
```

### Choose Your LLM

The app needs an LLM to turn transcripts into structured notes (topics, action items, etc.). Pick one:

**Option A — Local with Ollama (free, needs decent hardware)**

The config file is already set up for this. Just run:
```bash
docker compose --profile ollama up --build
```

Then pull the model (only needed the first time — it's a big download, ~18GB):
```bash
docker compose exec ollama ollama pull qwen2.5-coder:32b
```

If that model is too big for your machine, try a smaller one:
```bash
docker compose exec ollama ollama pull qwen2.5-coder:7b
```
Then update `llm_model` in your `config.yaml` to match.

**Option B — OpenAI or other API (costs money per use, works on any hardware)**

Edit `config.yaml` and change the LLM section:
```yaml
llm_provider: openai
llm_model: gpt-4o
llm_api_key: "sk-your-key-here"
llm_base_url: https://api.openai.com/v1
```

Then run without the Ollama profile:
```bash
docker compose up --build
```

### GPU Support (Optional)

If you have an NVIDIA GPU, the app can use it for much faster transcription. You need:
1. NVIDIA drivers installed
2. [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

Then add the GPU override when starting:
```bash
# With Ollama:
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile ollama up --build

# Without Ollama:
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

Without a GPU it still works — just slower for transcription (CPU mode).

### Use It

Open **http://localhost:3000** in your browser. Upload a meeting recording and it'll transcribe it with speaker labels, then extract topics, decisions, action items, and Q&A.

### Stopping / Restarting

```bash
# Stop everything
docker compose --profile ollama down

# Start again (your data is saved)
docker compose --profile ollama up
```

Your database and downloaded models are saved in Docker volumes, so nothing is lost between restarts.

### Troubleshooting

**"Cannot access the pyannote diarization model"**
Your HuggingFace token is missing or you haven't accepted the model terms. Double-check both steps under Prerequisites.

**Ollama model not found**
You need to pull it first: `docker compose exec ollama ollama pull qwen2.5-coder:32b`

**Build fails on PyTorch install**
The first build downloads ~2GB of PyTorch packages. Make sure you have a stable internet connection and enough disk space (~15GB for the full setup).

**Frontend loads but API calls fail**
Wait a few seconds after startup — the backend takes a moment to initialize. Check `docker compose logs backend` for errors.
