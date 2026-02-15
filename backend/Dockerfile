# ---- Stage 1: preload a tiny model into the image (optional but faster) ----
# FROM ollama/ollama:latest AS ollama
# RUN (ollama serve & sleep 2) \
#  && ollama pull tinyllama \
#  && pkill ollama || true

# ---- Stage 2: app image ----
FROM python:3.11-slim

# System deps for pydub + health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# App code
COPY . /app

# Ollama binary + cached model (optional)
# COPY --from=ollama /bin/ollama /usr/local/bin/ollama
# COPY --from=ollama /root/.ollama /root/.ollama

# Ensure start.sh is executable (and has LF line endings)
RUN chmod +x /app/start.sh

# Default envs (can be overridden at deploy)
ENV PORT=8080
# ENV OLLAMA_BASE_URL=http://127.0.0.1:11434
# ENV OLLAMA_MODEL=phi3:mini
ENV TOKENIZERS_PARALLELISM=false
ENV SENTENCE_TRANSFORMERS_HOME=/tmp/st-cache
ENV TRANSFORMERS_CACHE=/tmp/hf-cache

# Use the start script as entrypoint
ENTRYPOINT ["/app/start.sh"]