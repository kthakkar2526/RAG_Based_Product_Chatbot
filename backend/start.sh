#!/usr/bin/env bash
set -e

# # ---- 0) Defaults (override via env at deploy) ----
# export OLLAMA_MODEL="${OLLAMA_MODEL:-phi3:mini}"   # tiny + fast
# export OLLAMA_HOST=0.0.0.0:11434
# export OLLAMA_KEEP_ALIVE="10m"
# export CHROMA_PATH="${CHROMA_PATH:-/workspace/chroma_store}"

# # ---- 1) Start Ollama if present (don't block forever) ----
# if command -v ollama >/dev/null 2>&1; then
#   ollama serve &
#   # Try to pull the tiny model in background (don't block app start)
#   ( sleep 1; ollama pull "$OLLAMA_MODEL" || true ) &

#   # Wait up to ~8s so health checks aren’t blocked indefinitely
#   for i in {1..8}; do
#     if curl -s http://127.0.0.1:11434/api/tags >/dev/null; then
#       echo "Ollama is up."
#       break
#     fi
#     echo "Waiting for Ollama..."
#     sleep 1
#   done
# else
#   echo "ollama not found in image; skipping local LLM."
# fi


# ---- 3) Start FastAPI and bind to $PORT (required by Cloud Run) ----
echo "Starting FastAPI on port ${PORT:-8080}"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"