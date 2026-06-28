# Deploy: Railway (backend) + Vercel (dashboard)

This is the recommended path if you do **not** want a VPS.

| Part | Platform | What runs there |
|------|----------|-----------------|
| Dashboard | **Vercel** | Next.js frontend |
| API | **Railway** | FastAPI |
| Worker | **Railway** (2nd service) | ARQ — runs the agents |
| Database | **Railway Postgres** | Job storage |
| Queue | **Railway Redis** | Background jobs |
| LLM | **Groq** (free tier) | Replaces local Ollama |

> **Why not Ollama on Railway?** Ollama needs a large local model (1–4 GB RAM) and long-running inference. Railway/Vercel cannot run it reliably. **Groq** is free, fast, and works with a simple API key.

---

## What you need from you

| # | Item | Where to get it |
|---|------|-----------------|
| 1 | **GitHub repo** | Already at [ContentOrchester](https://github.com/Abhimanyusars/ContentOrchester) |
| 2 | **Railway account** | [railway.app](https://railway.app) |
| 3 | **Vercel account** | [vercel.com](https://vercel.com) |
| 4 | **Groq API key** (free) | [console.groq.com](https://console.groq.com) |
| 5 | **Tavily API key** | [tavily.com](https://tavily.com) |
| 6 | **JWT secret** | Run: `openssl rand -hex 32` |

**Cost estimate:** Railway hobby ~$5/mo credit + usage (API + Worker + Postgres + Redis). Vercel free tier is enough for the dashboard.

---

## Part 1 — Deploy backend on Railway

### Step 1: Create Railway project

1. Go to [railway.app/new](https://railway.app/new)
2. **Deploy from GitHub repo** → select `ContentOrchester`
3. Railway creates one service — we'll configure it as the **API**

### Step 2: Add Postgres and Redis

1. In your Railway project, click **+ New**
2. Add **PostgreSQL**
3. Click **+ New** again → add **Redis**

### Step 3: Configure the API service

1. Click the **API service** (from GitHub)
2. **Settings → Root Directory** → set to `backend`  
   (Required — all Python code and `Dockerfile` live in `backend/`)
3. **Settings → Config-as-code file** → set to `/backend/railway.toml`  
   (Or leave blank if root directory is `backend` — Railway auto-detects `railway.toml` there)
4. Confirm **Settings → Build** shows `Builder: Dockerfile` (from `railway.toml`)
5. **Settings → Networking → Generate Domain** → copy URL  
   Example: `https://contentorchester-api-production.up.railway.app`

> **Build failed from repo root?** Railway was looking at the monorepo root (no `requirements.txt` there). Root Directory **must** be `backend`.

### Step 4: Set API environment variables

Go to **API service → Variables** and add:

```env
STANDALONE_MODE=false
APP_ENV=production
DEBUG=false

LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_key
GROQ_MODEL=llama-3.1-8b-instant

TAVILY_API_KEY=tvly_your_key
JWT_SECRET=your_64_char_hex_secret

DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

CORS_ORIGINS=https://placeholder.vercel.app
```

> Update `CORS_ORIGINS` after Vercel deploy with your real Vercel URL.

### Step 5: Add the Worker service (critical for agents)

Agents **will not run** without this second service.

1. Click **+ New → GitHub Repo** → same `ContentOrchester` repo
2. **Settings → Root Directory** → `backend`
3. **Settings → Config-as-code file** → `/backend/railway.worker.toml`
4. **Variables** → copy the **same variables** as the API service (DATABASE_URL, REDIS_URL, GROQ, TAVILY, JWT, etc.)
5. Worker does **not** need a public domain

### Step 6: Verify API

```bash
curl https://YOUR-RAILWAY-API.up.railway.app/api/v1/health
```

Expected: `"status": "healthy"` with database, redis, and llm connected.

---

## Part 2 — Deploy dashboard on Vercel

### Step 1: Import project

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import `ContentOrchester` from GitHub
3. **Root Directory** → `frontend`
4. Framework: **Next.js** (auto-detected)

### Step 2: Environment variable

Add one variable:

| Name | Value |
|------|-------|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-RAILWAY-API.up.railway.app/api/v1` |

Use your real Railway API URL from Part 1 Step 3.

### Step 3: Deploy

Click **Deploy**. Vercel gives you a URL like `https://content-orchester.vercel.app`.

### Step 4: Update Railway CORS

Go back to Railway **API service → Variables** and set:

```env
CORS_ORIGINS=https://your-app.vercel.app
```

Redeploy the API service (Railway auto-redeploys on variable change).

---

## Part 3 — Test the full pipeline

1. Open your Vercel URL
2. Go to **Create Brief** (`/briefs/new`)
3. Submit a topic
4. Status page should progress: `research` → `write` → `seo` → `human_review`

If jobs stay **pending**:

```bash
# In Railway dashboard → Worker service → Logs
# Look for errors like Redis connection or Groq API failures
```

---

## Architecture

```
User browser
     │
     ▼
┌─────────────┐         ┌──────────────────────────────────┐
│   Vercel    │  HTTPS  │           Railway                │
│  (Next.js)  │────────▶│  API ──▶ Redis ◀── Worker (ARQ)  │
└─────────────┘         │   │              │               │
                        │   ▼              ▼               │
                        │ Postgres      Groq + Tavily      │
                        └──────────────────────────────────┘
```

---

## Will agents run automatically?

| After deploy | Status |
|--------------|--------|
| User submits brief | API enqueues job to Redis |
| Worker picks up job | Runs LangGraph agents |
| Groq handles LLM | Writer, Editor, SEO, etc. |
| Tavily handles search | Researcher agent |
| WebSocket updates | Live status on Vercel dashboard |

**Yes — automatically**, as long as:
- Worker service is running on Railway
- `STANDALONE_MODE=false`
- `GROQ_API_KEY` and `TAVILY_API_KEY` are valid
- `CORS_ORIGINS` matches your Vercel URL

---

## Local dev vs production

| Setting | Local (your Mac) | Railway production |
|---------|------------------|-------------------|
| `LLM_PROVIDER` | `ollama` | `groq` |
| `STANDALONE_MODE` | `true` | `false` |
| Worker | In-process | Separate Railway service |
| Database | SQLite | Railway Postgres |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails — no recognizable project files | **Root Directory** = `backend`; `builder = "DOCKERFILE"` in `railway.toml` |
| Invalid builder `nixpacks` | Use `DOCKERFILE` (already fixed in repo) |
| CORS error in browser | Set `CORS_ORIGINS` to exact Vercel URL (no trailing slash) |
| Jobs stuck on pending | Check Worker logs on Railway; ensure Redis URL is set |
| `401` on brief API | JWT issue — check `JWT_SECRET` matches on API + Worker |
| Frontend hits localhost | Rebuild Vercel with correct `NEXT_PUBLIC_API_URL` |
| Groq rate limit | Free tier has limits; wait or upgrade Groq plan |
| WebSocket not updating | Railway supports WS; ensure API URL uses `https` (Vercel uses `wss://`) |

---

## Updating after code changes

1. Push to `main` on GitHub
2. Railway auto-redeploys API + Worker
3. Vercel auto-redeploys frontend

No manual steps needed once connected.

---

## Quick checklist

- [ ] Railway: Postgres added
- [ ] Railway: Redis added
- [ ] Railway: API service (`backend/`, uvicorn)
- [ ] Railway: Worker service (`backend/`, arq)
- [ ] Railway: All env vars on **both** API and Worker
- [ ] Railway: Public domain generated for API
- [ ] Vercel: `frontend/` deployed
- [ ] Vercel: `NEXT_PUBLIC_API_URL` set
- [ ] Railway: `CORS_ORIGINS` = Vercel URL
- [ ] Health check returns healthy
- [ ] Test brief completes end-to-end
