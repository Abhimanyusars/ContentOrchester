# ContentOrchester — Production Deployment Guide

This guide deploys the full stack on a **single VPS** with Docker:

- **Caddy** — HTTPS reverse proxy
- **Next.js** — frontend
- **FastAPI** — API
- **ARQ worker** — runs LangGraph agents in the background
- **PostgreSQL** + **Redis** — data + job queue
- **Ollama** — local LLM (no paid API key)

---

## What you need before starting

### 1. A VPS (virtual server)

| Requirement | Minimum |
|-------------|---------|
| RAM | 4 GB (8 GB recommended) |
| CPU | 2 vCPUs |
| Disk | 25 GB SSD |
| OS | Ubuntu 22.04 or 24.04 |

**Suggested providers:** Hetzner CPX21, DigitalOcean Basic 4GB, AWS EC2 t3.medium.

### 2. A domain name (recommended)

Point your domain's **A record** to the VPS public IP:

```
yourdomain.com      →  YOUR_SERVER_IP
www.yourdomain.com  →  YOUR_SERVER_IP  (optional)
```

HTTPS is automatic via Caddy + Let's Encrypt.

> **No domain yet?** You can test with the server IP only, but you'll need to adjust `DOMAIN` and use HTTP (see [IP-only deploy](#ip-only-deploy-no-domain) below).

### 3. Secrets and keys (you provide these)

| Item | What it is | How to get it |
|------|------------|---------------|
| `TAVILY_API_KEY` | Web search for Researcher agent | [tavily.com](https://tavily.com/) — free tier |
| `JWT_SECRET` | Signs auth tokens | Run: `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | Database password | Any strong random string |
| `DOMAIN` | Your site URL | e.g. `contentorchester.com` |
| `ACME_EMAIL` | For SSL certificate emails | Your email |
| `PUBLIC_API_URL` | Frontend → API URL | `https://yourdomain.com/api/v1` |

### 4. Server access

- SSH login: `ssh root@YOUR_SERVER_IP` (or your sudo user)
- Open firewall ports **80** and **443**

---

## Step-by-step deployment

### Step 1 — Connect to your VPS

```bash
ssh root@YOUR_SERVER_IP
```

### Step 2 — Install Docker

```bash
apt update && apt upgrade -y
apt install -y docker.io docker-compose-plugin git curl
systemctl enable docker
systemctl start docker
```

### Step 3 — Clone the repo

```bash
git clone https://github.com/Abhimanyusars/ContentOrchester.git
cd ContentOrchester
```

### Step 4 — Create production `.env`

```bash
cp deploy/.env.production.example .env
nano .env   # or vim
```

Fill in every value marked `replace-with` or `yourdomain`:

```env
DOMAIN=yourdomain.com
ACME_EMAIL=you@yourdomain.com
PUBLIC_API_URL=https://yourdomain.com/api/v1
CORS_ORIGINS=https://yourdomain.com

TAVILY_API_KEY=tvly-xxxxxxxx
JWT_SECRET=<output of: openssl rand -hex 32>
POSTGRES_PASSWORD=<strong random password>

OLLAMA_MODEL=llama3.2:1b
STANDALONE_MODE=false
APP_ENV=production
DEBUG=false
```

### Step 5 — Open firewall

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### Step 6 — Deploy

```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

First run downloads the Ollama model (~1–2 GB) and can take **5–15 minutes**.

### Step 7 — Verify everything is running

```bash
docker compose -f docker-compose.prod.yml ps
curl -s https://yourdomain.com/api/v1/health | python3 -m json.tool
```

All containers should be `running` or `healthy`. Worker must be up for agents to process jobs.

### Step 8 — Test the agent pipeline

1. Open `https://yourdomain.com`
2. Go to **Create Brief** (`/briefs/new`)
3. Submit a topic
4. Watch the status page — nodes should move: research → write → seo → human_review
5. Approve to finish phase 2

Check worker logs if jobs stay pending:

```bash
docker compose -f docker-compose.prod.yml logs -f worker
```

---

## IP-only deploy (no domain)

For quick testing without a domain, use a simplified Caddy config:

1. Set in `.env`:
   ```env
   DOMAIN=:80
   PUBLIC_API_URL=http://YOUR_SERVER_IP/api/v1
   CORS_ORIGINS=http://YOUR_SERVER_IP
   ACME_EMAIL=admin@example.com
   ```

2. Deploy as normal. Site will be at `http://YOUR_SERVER_IP` (no HTTPS).

---

## What runs automatically after deploy?

| Component | Auto-starts? | Role |
|-----------|--------------|------|
| API | Yes (`restart: unless-stopped`) | Receives briefs |
| Worker | Yes | **Runs agents** — critical |
| Ollama | Yes | LLM inference |
| Postgres / Redis | Yes | Storage + queue |
| Caddy | Yes | HTTPS + routing |

**Agents run automatically** when a user submits a brief, as long as the **worker** container is healthy and Ollama has the model loaded.

### Expected performance

| Model | RAM | Speed on 4GB VPS |
|-------|-----|------------------|
| `llama3.2:1b` | ~2 GB | Slow but works (~2–5 min/job) |
| `llama3.2:3b` | ~4 GB+ | May OOM on 4GB servers |

---

## Useful commands

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs -f

# Worker logs (agent pipeline)
docker compose -f docker-compose.prod.yml logs -f worker

# Ollama — check model is loaded
docker compose -f docker-compose.prod.yml exec ollama ollama list

# Restart after .env changes
docker compose -f docker-compose.prod.yml up -d --build

# Stop everything
docker compose -f docker-compose.prod.yml down

# Stop and delete data (careful!)
docker compose -f docker-compose.prod.yml down -v
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Jobs stuck on `pending` | Check worker: `logs -f worker` |
| `connection refused` to Ollama | Wait for ollama healthcheck; check `ollama list` |
| Frontend calls wrong API | Rebuild frontend: `PUBLIC_API_URL` must match domain |
| CORS errors | Set `CORS_ORIGINS=https://yourdomain.com` in `.env`, restart api |
| SSL not working | DNS A record must point to server; ports 80/443 open |
| Out of memory | Use `llama3.2:1b` or upgrade VPS to 8GB |

---

## Updating the app

```bash
cd ContentOrchester
git pull
./deploy/deploy.sh
```

---

## Architecture (production)

```
Internet
   │
   ▼
┌─────────┐     ┌──────────┐     ┌─────────┐
│  Caddy  │────▶│ Frontend │     │   API   │
│  :443   │────▶│  :3000   │     │  :8000  │
└─────────┘     └──────────┘     └────┬────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              ┌──────────┐     ┌──────────┐     ┌──────────┐
              │  Worker  │     │ Postgres │     │  Redis   │
              │  (ARQ)   │     └──────────┘     └──────────┘
              └────┬─────┘
                   ▼
              ┌──────────┐     ┌──────────┐
              │  Ollama  │     │  Tavily  │
              │  (LLM)   │     │ (search) │
              └──────────┘     └──────────┘
```
