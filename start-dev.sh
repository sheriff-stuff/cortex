#!/usr/bin/env bash
# start-dev.sh — Start both backend and frontend for development
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for log prefixes
RED='\033[0;31m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

cleanup() {
    echo ""
    echo -e "${RED}Shutting down...${NC}"
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    [ -n "$OLLAMA_PID" ] && kill "$OLLAMA_PID" 2>/dev/null
    wait 2>/dev/null
    echo "Done."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# --- Install dependencies ---
echo -e "${GREEN}[setup]${NC} Installing backend dependencies..."
pip install -e ".[api]" --quiet 2>&1

echo -e "${GREEN}[setup]${NC} Installing frontend dependencies..."
(cd frontend && npm install --silent) 2>&1

# --- Start Ollama ---
if command -v ollama &> /dev/null; then
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${BLUE}[ollama]${NC} Starting Ollama..."
        ollama serve > /dev/null 2>&1 &
        OLLAMA_PID=$!
        # Wait for Ollama to be ready
        for i in $(seq 1 15); do
            if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo -e "${BLUE}[ollama]${NC} Ready!"
                break
            fi
            sleep 1
        done
    else
        echo -e "${BLUE}[ollama]${NC} Already running"
    fi
else
    echo -e "${RED}[ollama]${NC} WARNING: Ollama not found. LLM extraction will not work."
    echo -e "${RED}[ollama]${NC} Install from https://ollama.ai"
fi

# --- Start backend ---
echo -e "${BLUE}[backend]${NC} Starting API server on http://127.0.0.1:9000 ..."
meeting-notes serve --reload 2>&1 | sed "s/^/[backend] /" &
BACKEND_PID=$!

# Wait for backend to be ready
echo -e "${BLUE}[backend]${NC} Waiting for backend to be ready..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:9000/api/notes > /dev/null 2>&1; then
        echo -e "${BLUE}[backend]${NC} Ready!"
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "${RED}[backend]${NC} Failed to start. Check logs above."
        exit 1
    fi
    sleep 1
done

# --- Start frontend ---
echo -e "${GREEN}[frontend]${NC} Starting Vite dev server..."
(cd frontend && npm run dev) 2>&1 | sed "s/^/[frontend] /" &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo -e "  ${GREEN}App is running!${NC}"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://127.0.0.1:9000"
echo "  Press Ctrl+C to stop"
echo "========================================"
echo ""

# Wait for either process to exit
wait
