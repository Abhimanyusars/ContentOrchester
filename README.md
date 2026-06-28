# ContentOrchester

Multi-agent AI content creation system. Three specialized agents — **Researcher**, **Writer**, and **Editor** — collaborate via LangGraph to produce publication-ready content.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│  Next.js    │────▶│   FastAPI    │────▶│  Redis (ARQ task queue)     │
│  Dashboard  │     │   Backend    │     └──────────┬──────────────────┘
└─────────────┘     └──────┬───────┘                │
                           │                         ▼
                           │              ┌──────────────────────┐
                           │              │  ARQ Worker          │
                           │              │  (background jobs)   │
                           │              └──────────┬───────────┘
                           │                         │
                           ▼                         ▼
                    ┌──────────────┐     ┌─────────────────────────────┐
                    │  PostgreSQL  │     │  LangGraph Agent Pipeline   │
                    └──────────────┘     │  Researcher → Writer → Editor│
                                         └──────────┬──────────────────┘
                                                    │
                              ┌─────────────────────┼─────────────────────┐
                              ▼                     ▼                     ▼
                        ┌──────────┐         ┌──────────┐         ┌──────────┐
                        │  Tavily  │         │  Ollama  │         │  Ollama  │
                        │  Search  │         │  (local) │         │  (local) │
                        └──────────┘         └──────────┘         └──────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Uvicorn |
| Agent Orchestration | LangGraph |
| LLM | Ollama (free, local — llama3.2) |
| Web Search | Tavily (free tier) |
| Database | PostgreSQL + SQLAlchemy (async) |
| Task Queue | Redis + ARQ |
| Frontend | Next.js 15 + React 19 |

## Prerequisites

- Docker & Docker Compose
- API key:
  - [Tavily](https://tavily.com/) — free tier (1,000 searches/month)
- No LLM API key needed — Ollama runs locally in Docker

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your TAVILY_API_KEY
```

### 2. Start all services

```bash
docker compose up --build
```

This starts:
- **API** at http://localhost:8000
- **Dashboard** at http://localhost:3000
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **ARQ Worker** (background agent processing)

### 3. Create content

Open http://localhost:3000, enter a topic, and click **Generate Content**. The three agents will:

1. **Researcher** — searches the web via Tavily and synthesizes research notes
2. **Writer** — drafts content based on research
3. **Editor** — polishes the draft into final content

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL and Redis locally, then:
cp ../.env.example ../.env
# Set POSTGRES_HOST=localhost and REDIS_HOST=localhost in .env

uvicorn app.main:app --reload --port 8000

# In a separate terminal, start the worker:
arq app.workers.content_worker.WorkerSettings
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/content` | Create content job |
| GET | `/api/v1/content` | List all jobs |
| GET | `/api/v1/content/{id}` | Get job details |
| GET | `/api/v1/content/{id}/status` | Poll job status |
| DELETE | `/api/v1/content/{id}` | Delete a job |

Interactive docs: http://localhost:8000/docs

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph agents (researcher, writer, editor)
│   │   ├── api/routes/      # FastAPI route handlers
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic & external integrations
│   │   ├── workers/         # ARQ background workers
│   │   ├── config.py        # Settings from environment
│   │   ├── database.py      # Async PostgreSQL setup
│   │   ├── redis_client.py  # Async Redis client
│   │   └── main.py          # FastAPI app entry point
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── app/             # Next.js pages
│       └── lib/api.ts       # API client
├── docker-compose.yml
├── .env.example
└── README.md
```

## Production Deployment

| Stack | Guide |
|-------|-------|
| **Railway + Vercel** (recommended) | [DEPLOY_RAILWAY_VERCEL.md](./DEPLOY_RAILWAY_VERCEL.md) |
| VPS + Docker | [DEPLOY.md](./DEPLOY.md) |

## Next Steps

- Add authentication (JWT/OAuth)
- Support multiple content formats (Markdown export, PDF)
- Add a SEO optimizer agent
- Implement streaming responses for real-time agent progress
- Add rate limiting and usage tracking for API keys
