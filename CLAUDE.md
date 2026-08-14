# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

BACII Math Practice — students handwrite answers to Cambodian BAC II math problems and get instant,
mathematically-exact grading plus step-by-step explanations. Current topic: Complex Numbers (modulus,
argument, conjugate, real/imaginary parts); architecture is meant to extend to other BAC II topics later.

**Core principles that constrain design decisions:**
- **SymPy is the source of truth.** Answers and grading are always computed by SymPy (`backend/engine/solver.py`,
  `grader.py`), never by an LLM. Never let an LLM compute or validate a math answer directly.
- **LLMs only narrate and propose.** Gemini (Vertex AI) → Ollama → deterministic SymPy text is the fallback
  chain for turning SymPy's steps into friendly explanations. In Gemini generation mode, the LLM proposes a
  problem but SymPy still recomputes/validates the answer before it's accepted (`engine/generator.py`).
- **Handwriting OCR runs locally** via Ollama on the host (not in Docker), not a cloud vision API.

## Running the stack

Full stack (Postgres, Redis, backend, web) via Docker Compose:
```bash
docker compose up -d --build
# Web:      http://localhost:3016
# API docs: http://localhost:8016/docs
```

Prerequisite: Ollama running on the **host** (containers reach it via `host.docker.internal:11434`), with
`ollama pull qwen2.5vl:3b` (vision OCR, required) and optionally `qwen2.5:3b` (text fallback).

Backend only, without Docker:
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8016
```

Web only:
```bash
cd web
npm install
npm run dev     # http://localhost:3000 (dev server)
npm run build
npm run start
```

DB migrations (Alembic, run automatically on container startup; run manually otherwise):
```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "..."   # new migration after models.py changes
```

There is no test suite or lint config in this repo currently.

Reset the database: `docker compose down -v && docker compose up -d` (wipes all data).

API testing: Swagger UI at `/docs`, or import `bacii-math.postman_collection.json` — its
`Auth → Login/Signup` requests auto-populate the `{{token}}` collection variable used by other requests.

## Architecture

```
Next.js web (3016) --REST/JSON, Bearer JWT--> FastAPI backend (8016)
                                                  |         |         |        |
                                              Postgres   Redis    Ollama   Gemini
                                              (data)   (cache +  (host,   (Vertex AI,
                                                       rate-lim) vision)  explanations)
```

### Backend layout (`backend/`)
- `main.py` — FastAPI app, CORS, router registration.
- `routers/` — thin HTTP layer (`auth.py`, `problems.py`, `vision.py`); delegates to `services.py`.
- `services.py` — orchestration layer: wires `engine/` + `models.py` + `cache.py` together for each
  endpoint's use case (create question, grade, explain, stats). This is the place to look first to
  understand a request's full flow.
- `engine/` — the math/AI core, framework-agnostic:
  - `solver.py` — SymPy computation of exact answers + solution steps for each `question_type`.
  - `generator.py` — builds problems either from integer templates (`generation_mode="templates"`,
    keeps answers clean — Pythagorean triples for modulus, multiples of pi/4 for argument) or via
    Gemini proposal re-validated by SymPy (`generation_mode="gemini"`).
  - `grader.py` — compares a user answer against the SymPy-exact answer (exact or tolerance-based).
  - `explainer.py` — turns solver steps into deterministic plain-text explanation (LLM fallback baseline).
  - `llm.py` — Gemini (Vertex AI) client + Ollama text/vision calls, with the Gemini → Ollama →
    deterministic fallback chain and rate-limiting via `cache.allow_gemini`.
  - `vision.py` — image preprocessing (auto-crop to ink, upscale) before handing off to Ollama vision OCR.
- `models.py` — SQLAlchemy 2.0 async models: `User`, `Question`, `Step`, `Attempt`, `Explanation`.
- `schemas.py` — Pydantic request/response models.
- `cache.py` — Redis-backed explanation cache (keyed by `question_type:a:b`) and per-user Gemini
  rate limiting (`gemini_rate_limit_per_minute`, default 10/min).
- `core/config.py` — `pydantic-settings` Settings, loaded from env vars or `backend/.env`.
- `core/security.py` / `core/deps.py` — JWT (PyJWT + bcrypt) issuance/verification and FastAPI auth deps.
- `alembic/` — DB migrations.

### Explanation/grading flow worth knowing
`grade_question` in `services.py` always grades via `grader.grade()` (SymPy-backed) first. Only on an
incorrect answer does it build an explanation (`_build_explanation`) and run `llm.check_work` to comment
on the student's specific mistake. Explanations are cached in Redis by `(question_type, a, b)` so
identical questions reuse a previously-generated Gemini explanation instead of re-billing.

### Web layout (`web/src/`)
- `app/` — Next.js App Router pages: `/`, `/login`, `/signup`, `/practice`, `/history`, `/stats`.
- `components/` — `Canvas` (handwriting capture), `QuestionCard`, `Navbar`, `AuthGuard`.
- `context/AuthContext.tsx` — JWT stored in `localStorage`, exposes auth state to the app.
- `lib/api.ts` — typed API client; auto-refreshes the access token on a 401 using the refresh token.

### Handwriting detection flow
Canvas/upload image (base64) → `POST /vision/detect` → backend preprocesses (auto-crop + upscale,
`engine/vision.py`) → Ollama vision model (`qwen2.5vl:3b`) returns `{raw_text, latex, tokens, confidence}`
→ transcribed text is submitted to `POST /problems/grade`, graded by SymPy.

## Configuration

Backend settings (`backend/core/config.py`, overridable via env vars or `backend/.env`): `database_url`,
`redis_url`, `jwt_secret`, `gemini_model`/`gemini_location`, `ollama_url`, `vision_model`, `text_model`,
`gemini_rate_limit_per_minute`, `explanation_cache_ttl_seconds`. In Docker Compose these are injected
directly as environment variables (see `docker-compose.yml`); `GOOGLE_APPLICATION_CREDENTIALS` points at
a mounted `backend/credentials/gemini-service-account.json` (gitignored).

Web reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8016`).

## Adding a new topic

The complex-numbers implementation is the template for extending to other BAC II topics (functions,
geometry, differential equations, integrals, conics, probability): add a solver for the topic's
question types in `engine/solver.py`, template/Gemini generation in `engine/generator.py`, grading rules
in `engine/grader.py`, and extend `QUESTION_TYPES` accordingly — `services.py` and the routers are
already topic-agnostic (topic is just a field on `Question`).
