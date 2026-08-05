
# StudyDeck — Deployment Plan

**Frontend:** GitHub Pages (free, static hosting)
**Backend:** Render (free tier, FastAPI)
**Database:** Supabase (already live)

---

## Overview

```
Browser → GitHub Pages (HTML/CSS/JS)
              ↓ fetch requests
         Render (FastAPI)
              ↓ SQL
         Supabase (PostgreSQL)
```

---

## Phase 1 — Prepare the codebase (do this first, locally)

### Task 1.1 — Update BASE_URL in every frontend file

Every HTML page and `api.js` has `BASE_URL = 'http://localhost:8000'`.
Change it to your Render URL in every file before deploying.

Files to update (change the BASE_URL line in each):
- `studydeck/frontend/assets/js/api.js`
- `studydeck/frontend/index.html`
- `studydeck/frontend/login.html`
- `studydeck/frontend/register.html`
- `studydeck/frontend/dashboard.html`
- `studydeck/frontend/deck.html`
- `studydeck/frontend/study.html`
- `studydeck/frontend/quiz.html`
- `studydeck/frontend/ai-generate.html`

Change:
```js
const BASE_URL = 'http://localhost:8000';
```
To:
```js
const BASE_URL = 'https://YOUR-APP-NAME.onrender.com';
```
> You will get this URL after completing Phase 2. Come back and do this step then.

---

### Task 1.2 — Add `render.yaml` for Render deployment

Create `studydeck/backend/render.yaml`:
```yaml
services:
  - type: web
    name: studydeck-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: SECRET_KEY
        sync: false
      - key: OPENAI_API_KEY
        sync: false
```

---

### Task 1.3 — Add `requirements.txt` Python version pin

Add this line at the top of `studydeck/backend/requirements.txt`:
```
# Python 3.11
```
Render needs to know which Python to use. Also create `studydeck/backend/runtime.txt`:
```
python-3.11.0
```

---

### Task 1.4 — Update CORS in `main.py` for production

After you know your GitHub Pages URL (format: `https://YOUR-USERNAME.github.io`),
update the CORS section in `studydeck/backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://YOUR-USERNAME.github.io",
        "http://localhost:5500",   # for local dev with Live Server
        "http://127.0.0.1:5500",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### Task 1.5 — Push code to GitHub

1. Go to [github.com](https://github.com) → New repository → name it `studydeck`
2. Make it **Public** (required for free GitHub Pages)
3. From your project root run:

```powershell
cd "e:\Masai Capstone"
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/studydeck.git
git push -u origin main
```

> Make sure `.env` is in `.gitignore` — it already is since `studydeck/backend/.gitignore` includes `.env`.
> Double-check before pushing: never commit real API keys.

---

## Phase 2 — Deploy backend to Render

### Task 2.1 — Create Render account

- Go to [render.com](https://render.com) → Sign up with GitHub

### Task 2.2 — Create a new Web Service

1. Dashboard → **New** → **Web Service**
2. Connect your GitHub repo `studydeck`
3. Fill in:

| Field | Value |
|---|---|
| Name | `studydeck-api` |
| Root Directory | `studydeck/backend` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | `Free` |

### Task 2.3 — Add environment variables in Render

In the Render dashboard → your service → **Environment** tab, add:

| Key | Value |
|---|---|
| `SUPABASE_URL` | your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | your service_role key |
| `SECRET_KEY` | your random secret string |
| `OPENAI_API_KEY` | your OpenAI key |

> Do NOT set these in `render.yaml` — always set secrets through the dashboard.

### Task 2.4 — Verify backend is live

After deploy finishes (takes ~3 minutes), visit:
```
https://studydeck-api.onrender.com/health
```
You should see:
```json
{"status": "ok"}
```

Also test:
```
https://studydeck-api.onrender.com/decks
```
Should return `{"decks": [], "total": 0, "page": 1, "pages": 1}`.

---

## Phase 3 — Deploy frontend to GitHub Pages

### Task 3.1 — Complete Task 1.1 (update BASE_URL)

Now that you have your Render URL, go back and update `BASE_URL` in all 9 files listed in Task 1.1. Commit and push:

```powershell
git add studydeck/frontend/
git commit -m "Set production BASE_URL to Render backend"
git push
```

### Task 3.2 — Enable GitHub Pages

1. Go to your GitHub repo → **Settings** → **Pages**
2. Under **Source**, select:
   - Branch: `main`
   - Folder: `/studydeck/frontend` — **GitHub Pages does not support subdirectories directly**

> ⚠️ GitHub Pages only supports root `/` or `/docs` as the source folder.
> You have two options:

**Option A (recommended) — copy frontend to `/docs`:**
```powershell
cd "e:\Masai Capstone"
xcopy studydeck\frontend docs /E /I /Y
git add docs/
git commit -m "Add docs folder for GitHub Pages"
git push
```
Then set GitHub Pages source to: Branch `main`, Folder `/docs`.

**Option B — move frontend to repo root:**
Move all files from `studydeck/frontend/` to the repo root. More disruptive.

Go with Option A.

### Task 3.3 — Set Pages source and get URL

1. After pushing the `docs/` folder, go to Settings → Pages
2. Set Source → `main` branch → `/docs` folder → **Save**
3. Wait ~1 minute
4. Your site will be live at:
   ```
   https://YOUR-USERNAME.github.io/studydeck/
   ```

### Task 3.4 — Verify frontend is live

Open the URL in a browser. Test:
- [ ] `index.html` loads and shows the explore page
- [ ] Register a new account
- [ ] Login works and redirects to dashboard
- [ ] Create a deck
- [ ] Add cards
- [ ] Start a study session

---

## Phase 4 — Final checks

### Task 4.1 — Update CORS with real GitHub Pages URL

Now that you know your exact GitHub Pages URL, update `main.py` CORS:
```python
allow_origins=[
    "https://YOUR-USERNAME.github.io",
]
```
Commit, push → Render auto-redeploys.

### Task 4.2 — Free tier limitations to know

**Render free tier:**
- Spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds to wake up
- 750 free hours/month (enough for one service running all month)

**GitHub Pages:**
- 1 GB storage limit (fine for this project)
- 100 GB bandwidth/month (more than enough)
- No server-side logic — static files only (which is all we need)

---

## Quick reference — final URLs

| Service | URL |
|---|---|
| Frontend | `https://YOUR-USERNAME.github.io/studydeck/` |
| Backend | `https://studydeck-api.onrender.com` |
| API docs | `https://studydeck-api.onrender.com/docs` |
| Health check | `https://studydeck-api.onrender.com/health` |

---

## Deployment checklist

- [ ] 1.1 BASE_URL updated in all 9 frontend files
- [ ] 1.2 `render.yaml` created
- [ ] 1.3 `runtime.txt` created
- [ ] 1.4 CORS updated with GitHub Pages URL
- [ ] 1.5 Code pushed to GitHub (no `.env` committed)
- [ ] 2.1 Render account created
- [ ] 2.2 Web service created with correct settings
- [ ] 2.3 Environment variables set in Render dashboard
- [ ] 2.4 `/health` endpoint returns `{"status": "ok"}`
- [ ] 3.1 BASE_URL updated with real Render URL, pushed
- [ ] 3.2 `docs/` folder created and pushed
- [ ] 3.3 GitHub Pages source set to `/docs`
- [ ] 3.4 Frontend live and all flows tested
- [ ] 4.1 CORS locked to GitHub Pages URL only
