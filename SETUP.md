# Setup Guide

## Prerequisites

- **Docker Desktop** (with Compose) — for the whole stack
- **Ollama** installed and running **on the host** (not in Docker) with two models:
  ```bash
  ollama pull qwen2.5vl:3b   # vision — reads handwriting (required)
  ollama pull qwen2.5:3b     # text — explanation fallback (optional)
  ```
- **Vertex AI service account** (optional but recommended) for Gemini explanations:
  - Create a service account in Google Cloud with Vertex AI enabled
  - Download its JSON key and place it at `backend/credentials/gemini-service-account.json`
  - If omitted, explanations fall back to Ollama → deterministic text

---

## Quick start (everything in Docker)

```bash
cd BACII

# 1. (optional) generate a real JWT secret and tell the stack about it
#    on Windows PowerShell:
#    $b = New-Object byte[] 48
#    (New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($b)
#    [Convert]::ToBase64String($b)
#    then set $env:JWT_SECRET to that value

# 2. build & start the whole stack
docker compose up -d --build

# 3. open the app
#    Web app:    http://localhost:3016
#    API docs:   http://localhost:8016/docs
```

That one command builds and starts four services: **postgres, redis, backend, web**.

> **First build note:** the web image's `npm install` is the slow step. The Dockerfile is optimized
> (fast npm mirror + BuildKit cache mount), so it's one-time; later builds are seconds.
> `node_modules` lives only inside the container — no Windows install needed.

---

## Configuration

The backend reads settings from environment variables (or a `backend/.env` file). The important ones:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/bacii` | Postgres connection (compose overrides to the `postgres` service) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection (compose overrides) |
| `JWT_SECRET` | dev default | **Set a real value in production** |
| `GOOGLE_APPLICATION_CREDENTIALS` | `backend/credentials/gemini-service-account.json` | Vertex AI key path |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model for explanations |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama API (compose points at the host via `host.docker.internal`) |
| `VISION_MODEL` | `qwen2.5vl:3b` | Ollama vision model for handwriting OCR |
| `TEXT_MODEL` | `qwen2.5:3b` | Ollama text model (explanation fallback) |

The web app reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8016`), set in `docker-compose.yml`.

---

## Using the app

1. Open `http://localhost:3016` and **Sign up** (or log in).
2. Go to **Practice** and click **New Question**.
3. **Draw your answer** on the canvas — or click *Upload image...* to use a photo, or just type the answer.
4. Click **Check Answer**. The app detects the handwriting (Ollama), grades it with SymPy, and shows:
   - correct / incorrect + the expected answer
   - a concise step-by-step explanation (auto-shown on wrong answers)
5. See **History** and **Stats** for your progress.

> For best handwriting accuracy: draw the answer **large** and write just the answer value
> (e.g. `5`, `pi/4`, `3 - 4i`), not the full equation.

---

## Working without Docker (backend only, for development)

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8016
```

Migrations run automatically via Alembic on startup when Dockerized. To run them manually:
```bash
cd backend
alembic upgrade head
```

---

## API testing

- Interactive Swagger UI: `http://localhost:8016/docs`
- Postman: import `bacii-math.postman_collection.json` (repo root). The `Auth → Login/Signup`
  requests automatically store the access token into the collection variable `{{token}}`,
  which every other request uses.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Handwriting returns "nothing detected" | Draw larger; make sure Ollama is running and `qwen2.5vl:3b` is pulled. |
| Web app can't reach the API | Confirm CORS: backend allows `http://localhost:3016`. Both services must be up (`docker compose ps`). |
| Backend can't reach Ollama | Ollama must run on the **host**; containers reach it via `host.docker.internal:11434`. |
| Explanations are deterministic (not AI) | Gemini key missing/invalid, or rate-limited (10/min/user). Check `backend/credentials/gemini-service-account.json`. |
| Slow first web build | Expected on slow networks (npm mirror helps). Let it finish once — later builds are cached. |
| Reset the database | `docker compose down -v` then `docker compose up -d` (wipes all data). |
