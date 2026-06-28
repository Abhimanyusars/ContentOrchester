# Railway Step 1 — Backend API only

Complete these **in order**. Do not skip ahead to Generate Domain until step 8 shows **Success**.

---

## Step 1 — Create project + database

1. Go to [railway.app/new](https://railway.app/new)
2. **Deploy from GitHub** → select `ContentOrchester`
3. Click **+ New** → **Database** → **PostgreSQL**
4. Click **+ New** → **Database** → **Redis**

You should now see **3 boxes**: GitHub service, Postgres, Redis.

---

## Step 2 — Configure the GitHub service (API)

1. Click the **GitHub / ContentOrchester** box (not Postgres, not Redis)
2. Click **Settings** (top tab)
3. Find **Source** section:
   - **Root Directory** → type `backend` → Save
4. Find **Build** section — should say **Dockerfile** (from `railway.toml`)

---

## Step 3 — Add variables (required before deploy works)

1. Click **Variables** tab (same GitHub service)
2. Click **RAW Editor** and paste (replace the two `REPLACE_` values):

```env
STANDALONE_MODE=false
APP_ENV=production
DEBUG=false

LLM_PROVIDER=groq
GROQ_API_KEY=REPLACE_WITH_YOUR_GROQ_KEY
GROQ_MODEL=llama-3.1-8b-instant

TAVILY_API_KEY=REPLACE_WITH_YOUR_TAVILY_KEY
JWT_SECRET=REPLACE_WITH_openssl_rand_hex_32_output

DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

CORS_ORIGINS=http://localhost:3000
```

3. For `DATABASE_URL` and `REDIS_URL` — if RAW editor doesn't expand references, add them manually:
   - Click **+ New Variable** → **Add Reference** → Postgres → `DATABASE_URL`
   - Click **+ New Variable** → **Add Reference** → Redis → `REDIS_URL`

Generate JWT secret on your Mac:
```bash
openssl rand -hex 32
```

---

## Step 4 — Deploy

1. Click **Deployments** tab
2. Click **Deploy** or **Redeploy** (top right)
3. Wait 3–5 minutes — click the latest deployment to watch logs

### Build should show:
```
Building with Dockerfile
...
Successfully built
```

### Deploy logs should show:
```
app_starting
database_initialized
Uvicorn running on http://0.0.0.0:XXXX
```

### If deploy is RED / crashed:
Click the deployment → **View logs** → copy the last 20 lines and share (hide API keys).

Common errors:
| Error | Fix |
|-------|-----|
| `connection refused` to localhost postgres | Set `STANDALONE_MODE=false` + `DATABASE_URL=${{Postgres.DATABASE_URL}}` |
| `sslmode` / SSL error | Push latest code (SSL fix in `database.py`) |
| `GROQ_API_KEY is required` | Set `LLM_PROVIDER=groq` and your Groq key |
| Build from repo root | Root Directory must be `backend` |

---

## Step 5 — Generate public URL (only after green deploy)

Domain button appears only when the service is **running**.

1. Click the **GitHub service**
2. **Settings** → scroll to **Networking**
3. Under **Public Networking**:
   - Click **Generate Domain** (or **+ Domain**)
4. Copy URL: `https://something.up.railway.app`

### If you only see port `8080`:
- Change port to **`8000`** (or check deploy logs for the actual `$PORT` value)
- Click **Generate Domain** next to it
- If no button: deploy is not healthy yet — go back to Step 4 logs

### CLI fallback (on your Mac):
```bash
npm i -g @railway/cli
railway login
cd "/Users/abhimanyusarswat/my Agent/backend"
railway link
railway domain --port 8000
```

---

## Step 6 — Verify

```bash
curl https://YOUR-URL.up.railway.app/api/v1/health
```

Expected:
```json
{
  "status": "healthy",
  "services": {
    "database": { "status": "healthy" },
    "redis": { "status": "healthy" },
    "llm": { "provider": "groq", "status": "healthy" }
  }
}
```

`degraded` is OK for now if only LLM is slow to respond — `unhealthy` or connection error is not OK.

---

## Step 1 complete checklist

- [ ] Postgres added to project
- [ ] Redis added to project
- [ ] Root Directory = `backend`
- [ ] All variables set (especially `STANDALONE_MODE=false`, `DATABASE_URL`, `GROQ_API_KEY`)
- [ ] Latest code pushed to GitHub
- [ ] Deployment status = **Success** (green)
- [ ] Public domain generated
- [ ] Health check returns JSON

---

## After Step 1

Tell me:
1. Your Railway URL
2. Whether health check worked
3. Screenshot or paste of deploy error if still red

Then we do **Step 2: Vercel** and **Step 3: Worker service**.
