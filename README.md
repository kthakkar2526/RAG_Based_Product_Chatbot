# RAG-Based Product Chatbot

An AI-powered machine shop assistant that helps machinists maintain, troubleshoot, and operate CNC machines and industrial equipment. It uses Retrieval-Augmented Generation (RAG) to provide answers grounded in machine manuals and worker notes.

## Features

- **Hybrid RAG Search** — Combines semantic vector search (pgvector) with BM25 keyword ranking for accurate retrieval
- **Machine-Specific Filtering** — Select a machine to scope queries to relevant manuals and notes
- **Audio Transcription** — Record voice notes hands-free with automatic speech-to-text
- **Worker Notes** — Save and share shop floor notes that become part of the knowledge base
- **AI Chat** — Google Gemini-powered Q&A with source citations and markdown formatting
- **JWT Authentication** — Multi-user login with secure token-based auth

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Vite, Tailwind CSS, Framer Motion |
| Backend | FastAPI, LangChain, Sentence Transformers |
| Database | PostgreSQL + pgvector |
| LLM | Google Gemini 2.5 Flash |
| Embeddings | all-MiniLM-L6-v2 (384-dim) |
| Deployment | Docker, Google Cloud Run, Cloud Build CI/CD |

## Supported Machines

- Haas VF-2 / VF-5 (Vertical CNC Mills)
- Haas UMC-750 (5-Axis CNC Mill)
- Haas ST-20Y (CNC Turning Center)
- UR10e (Collaborative Robot)
- Ingersoll Rand R11i (Rotary Screw Compressor)
- Mitutoyo SJ-210 (Surface Roughness Tester)

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector) extension
- ffmpeg (for audio processing)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/RAG-Based-Product-Chatbot.git
cd RAG-Based-Product-Chatbot
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_DB=notes_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=<your-db-password>
JWT_SECRET_KEY=<your-jwt-secret>
GEMINI_API_KEY=<your-gemini-api-key>
AUTH_USERNAME_1=<username>
AUTH_PASSWORD_1=<password>
```

Ingest machine manuals and seed sample notes:

```bash
python -m scripts.ingest_manuals
python -m scripts.seed_notes
```

Start the server:

```bash
uvicorn main:app --reload --port 8080
```

### 3. Frontend

```bash
cd frontend
npm install
```

Create a `.env` file in `frontend/`:

```env
VITE_BACKEND_URL=http://localhost:8080
```

Start the dev server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/login/` | Authenticate and receive JWT token |
| GET | `/api/machines/` | List available machines |
| POST | `/api/chat/` | Query the RAG system (supports machine filtering) |
| POST | `/api/save_note/` | Save a worker note with auto-embedding |
| POST | `/api/transcribe/` | Upload audio file for transcription |

## How RAG Works

1. **PDF Ingestion** — Machine manuals are extracted, chunked (~800 tokens), and embedded
2. **Hybrid Retrieval** — Queries run through both semantic search and BM25 keyword matching
3. **Score Fusion** — Results are combined with weighted scoring (60% semantic, 40% BM25)
4. **Machine Filtering** — Optionally scoped to a specific machine's manuals and related notes
5. **LLM Generation** — Retrieved context is sent to Gemini to generate a grounded answer with citations

## Deployment

The project includes Docker configurations and a `cloudbuild.yaml` for deploying to Google Cloud Run:

```bash
gcloud builds submit --config cloudbuild.yaml
```

Services deployed:
- **Backend** — `demo-rag` (2 CPU, 2GB RAM, Cloud SQL proxy)
- **Frontend** — `demo-rag-frontend` (1 CPU, 512MB RAM, nginx)

## Project Structure

```
├── backend/
│   ├── rag/                # RAG pipeline (chatbot, vector store, DB, PDF ingestion)
│   ├── scripts/            # Data ingestion and seeding scripts
│   ├── manuals/            # Machine manual PDFs
│   ├── main.py             # FastAPI application
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/          # Chat, Record, Home, Login
│   │   └── components/     # Reusable UI components
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
└── cloudbuild.yaml         # CI/CD pipeline
```

## License

This project is for demonstration and educational purposes.
