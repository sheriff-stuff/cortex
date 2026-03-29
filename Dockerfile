FROM python:3.10-slim-bookworm

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git ffmpeg libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install PyTorch first (large, benefits from layer caching)
RUN pip install --no-cache-dir \
    torch torchvision torchaudio \
    --index-url ${TORCH_INDEX_URL}

# Copy and install project
COPY pyproject.toml .
COPY api/ api/
RUN pip install --no-cache-dir -e ".[api]"

# Create data directory for SQLite persistence
RUN mkdir -p /app/data

EXPOSE 9000

CMD ["meeting-notes", "serve", "--host", "0.0.0.0", "--port", "9000", "--config", "/app/config.yaml"]
