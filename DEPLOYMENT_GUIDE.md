# ClipPilot AI — Complete Online Hosting & Deployment Guide

This guide explains how to host **ClipPilot AI** online for free or low-cost production hosting.

---

## 1. Architecture Requirements

Unlike simple static websites or pure Node.js CRUD apps, **ClipPilot AI is a video processing engine**. It requires:
1. **FFmpeg & FFprobe installed in the OS** (to perform real video slicing, silence removal, subtitle rendering, and aspect cropping).
2. **A Python 3.10+ runtime with FastAPI**.
3. **A React SPA Frontend** (built with Vite & Tailwind CSS).

Because of the FFmpeg requirement, serverless function providers (like raw Vercel or Netlify Serverless Functions) cannot process videos. The backend must be hosted in an environment that supports **Linux packages or Docker containers**.

We have provided three deployment options:
- **Option 1 (Recommended — Easiest & Free):** Deploy Full-Stack as a single Docker container on **Render.com** or **Railway.app** (1 URL, zero CORS issues, free SSL).
- **Option 2 (Decoupled):** Deploy the **Frontend on Vercel** and the **Backend on Render/Railway**.
- **Option 3 (Self-Hosted VPS):** Deploy to **DigitalOcean / AWS / Hetzner** using `docker-compose`.

---

## Option 1: 1-Click Full-Stack Deploy on Render.com (Recommended & Free)

Deploy the entire app (Frontend + Backend + FFmpeg) on a single free Render Web Service.

### Step 1: Push Your Code to GitHub
Ensure your latest code is pushed to your GitHub repository:
```bash
git add .
git commit -m "Add Docker and deployment configuration"
git push origin main
```

### Step 2: Create a Web Service on Render
1. Sign in to [Render.com](https://render.com) (free account).
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository (`Incubrix` or your fork).
4. Configure the service settings:
   - **Name:** `clippilot-ai` (or your preferred name)
   - **Region:** Any (e.g. `Oregon (US West)` or `Frankfurt (EU)`)
   - **Branch:** `main`
   - **Runtime:** **Docker** *(Render will automatically use the root `Dockerfile`)*
   - **Instance Type:** **Free**
5. Under **Environment Variables**, add:
   | Key | Value | Notes |
   | :--- | :--- | :--- |
   | `PORT` | `8000` | Port for the container |
   | `CORS_ORIGINS` | `*` | Permits requests |
6. Click **Deploy Web Service**.

### Step 3: Access Your Live Application
Render will build the React frontend, package Python 3.11 with FFmpeg, and start FastAPI. Within 3–4 minutes, your app will be live at:
`https://clippilot-ai.onrender.com`

- Visiting `https://clippilot-ai.onrender.com/` opens the **ClipPilot Studio UI**.
- Visiting `https://clippilot-ai.onrender.com/docs` opens the **Interactive Swagger API Docs**.

---

## Option 2: 1-Click Deploy on Railway.app

[Railway.app](https://railway.app) provides generous trials and fast builds.

1. Sign in to [Railway.app](https://railway.app) with GitHub.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select your repository.
4. Railway will automatically detect the root `Dockerfile`.
5. Under **Settings**:
   - Set **Networking** → Click **Generate Domain**.
   - Under **Variables**, add:
     - `PORT` = `8000`
     - `CORS_ORIGINS` = `*`
6. *(Optional)* Add a Persistent Volume:
   - Go to your service → **Volumes** → **Add Volume**.
   - Mount Path: `/app/storage` (this preserves SQLite databases and processed videos across container redeploys).

---

## Option 3: Decoupled Deploy (Frontend on Vercel + Backend on Render)

If you prefer hosting the React frontend on Vercel's global CDN:

### Part A: Deploy the Backend on Render (or Railway)
1. In Render, create a **Web Service** from your GitHub repo.
2. Set **Runtime:** `Docker`.
3. Set **Dockerfile Path:** `Dockerfile.backend`.
4. Add Environment Variable:
   - `PORT`: `8000`
   - `CORS_ORIGINS`: `https://your-app.vercel.app` (your frontend Vercel URL)
5. Deploy. You will receive a backend URL like `https://clippilot-backend.onrender.com`.

### Part B: Deploy the Frontend on Vercel
1. Sign in to [Vercel](https://vercel.com).
2. Click **Add New...** → **Project**, and select your repository.
3. Configure the project settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click `Edit` and select `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Under **Environment Variables**, add:
   | Name | Value |
   | :--- | :--- |
   | `VITE_API_BASE_URL` | `https://clippilot-backend.onrender.com/api` |
5. Click **Deploy**.
*(Note: `frontend/vercel.json` is already configured for single-page routing).*

---

## Option 4: Self-Hosted Cloud VPS (DigitalOcean / AWS / Hetzner)

For high-speed video processing without free-tier CPU throttling, deploy to any Linux VPS ($4–$6/mo):

### 1. Connect to your VPS via SSH
```bash
ssh root@your-server-ip
```

### 2. Install Docker & Docker Compose
```bash
curl -fsSL https://get.docker.com | sh
```

### 3. Clone Repository & Run
```bash
git clone https://github.com/Varnika2005/Incubrix.git clippilot
cd clippilot
docker compose up -d --build
```

### 4. Configure HTTPS with Caddy (Automated Free SSL)
Install Caddy:
```bash
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install caddy -y
```

Edit `/etc/caddy/Caddyfile`:
```caddy
yourdomain.com {
    reverse_proxy localhost:8000
}
```

Reload Caddy:
```bash
systemctl reload caddy
```
Your application will be live at `https://yourdomain.com` with auto-renewing SSL!

---

## Summary of Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port on which the web server listens |
| `CORS_ORIGINS` | `*` (or comma-separated URLs) | Allowed origins for browser fetch requests |
| `VITE_API_BASE_URL` | `/api` | Base API URL used by the React client |
| `GEMINI_API_KEY` | *(Optional)* | For optional LLM-assisted prompt parsing |
| `OPENAI_API_KEY` | *(Optional)* | For optional LLM-assisted prompt parsing |

---

## Verification After Deployment
Once deployed, verify your live system by visiting:
1. `https://<YOUR_APP_URL>/api/health` — Confirms FastAPI backend is healthy.
2. `https://<YOUR_APP_URL>/api/capabilities` — Confirms FFmpeg 9.0+ and media tools are detected.
3. `https://<YOUR_APP_URL>/` — Confirms the ClipPilot AI studio is operational.
4. Click **1-Click Demo** to run a synthetic test video through the processing pipeline.
