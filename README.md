# BACII Math Practice

An app for **Cambodian BAC II (high-school) math practice** where students **handwrite** their answers and get **instant, mathematically-exact grading** plus **concise step-by-step explanations**.

## Our goal

Traditional practice apps make you type answers. We let you write them the way you do in the exam — by hand — then check if you're right, and when you're wrong, explain the correct solution step by step, the way a tutor would (but concise, no rambling).

The current focus is **Complex Numbers** (modulus, argument, conjugate, real/imaginary parts). The architecture is built to extend to every BAC II topic:

- Functions & Graphing
- Geometry in Space
- Complex Numbers *(current)*
- Differential Equations
- Integrals
- Conics
- Probability

### Core principles

1. **SymPy is the source of truth.** The correct answer and the grading are always computed by SymPy — a computer algebra system — never by an LLM. LLMs cannot be trusted to do arithmetic; SymPy cannot be wrong.
2. **LLMs only explain and propose.** Gemini (with a local Ollama fallback) rewrites SymPy's solution steps into friendly language and can suggest problem variations — but SymPy validates everything.
3. **Handwriting is detected locally** via Ollama (private, offline-capable), with server-side preprocessing (auto-crop + upscale) for accuracy.
4. **Everything runs in Docker** — backend, Postgres, Redis, and the web app — one command.

---

## Architecture — how each connection works

```
        ┌────────────────────────────────────────────┐
        │  Browser — Next.js web app (localhost:3016) │
        │  signup/login · practice canvas · history   │
        └──────────────────┬─────────────────────────┘
                           │  REST/JSON over CORS
                           │  Authorization: Bearer <JWT>
                           ▼
        ┌────────────────────────────────────────────┐
        │  FastAPI backend (localhost:8016)           │
        │  /auth       → JWT (bcrypt + PyJWT)         │
        │  /problems   → SymPy engine (generate/grade/explain)
        │  /vision     → handwriting OCR              │
        │  /attempts /stats                           │
        └───┬──────────┬──────────┬─────────┬────────┘
            │          │          │         │
        PostgreSQL   Redis      Ollama    Gemini (Vertex AI)
        (:5432)    (:6379)    (host:11434)   (cloud)
        persistent  cache +   qwen2.5vl:3b  step-by-step
        data        rate-limit vision OCR   explanations
```

### Connection details

| Connection | How it works |
|---|---|
| **Web → Backend** | JSON REST with JWT access/refresh tokens. The web app stores tokens in `localStorage`, sends `Authorization: Bearer <access>`, and auto-refreshes on a 401. CORS allows `http://localhost:3016`. |
| **Backend → PostgreSQL** | SQLAlchemy 2.0 (async, `asyncpg`). Stores everything: users, questions, solution steps, answer attempts, explanations. Migrations via Alembic (run automatically on container startup). |
| **Backend → Redis** | `redis.asyncio`. Two jobs: (1) **cache explanations** by question — identical questions reuse the AI answer instead of re-billing Gemini; (2) **rate-limit Gemini** to 10 calls/min/user to control cost. |
| **Backend → Ollama** | Async `httpx` to the host's Ollama (`host.docker.internal:11434`). Two models: `qwen2.5vl:3b` (vision — reads the handwriting) and `qwen2.5:3b` (text — explanation fallback). |
| **Backend → Gemini** | `google-genai` async client, Vertex AI service account. Produces the concise step-by-step explanations. If it fails or is rate-limited, the chain falls back **Gemini → Ollama → deterministic SymPy text**. |

### The handwriting detection flow

1. Student draws on the canvas (or uploads a photo).
2. Browser sends the image as base64 to `POST /vision/detect`.
3. Backend **preprocesses** it — auto-crops to the ink strokes and upscales so digits are big and clear.
4. The image goes to Ollama's vision model (`qwen2.5vl:3b`), which returns `{raw_text, latex, tokens, confidence}`.
5. The transcribed answer is sent to `POST /problems/grade`, where SymPy grades it.

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router) + React + TypeScript + Tailwind CSS |
| Backend | FastAPI (async) |
| Math engine | SymPy (source of truth for answers + grading) |
| Database | PostgreSQL 16 (SQLAlchemy 2.0 async / asyncpg, Alembic migrations) |
| Cache / rate-limit | Redis 7 |
| Auth | bcrypt + JWT (PyJWT): access (15 min) + refresh (7 days, rotation) |
| Explanations | Gemini (Vertex AI) → Ollama → deterministic fallback |
| Handwriting OCR | Ollama `qwen2.5vl:3b` (local) |
| Orchestration | Docker Compose |

---

## Repo layout

```
BACII/
├── backend/           # FastAPI + engine + auth + persistence
│   ├── core/          # config, security (JWT), dependencies
│   ├── engine/        # solver, generator, grader, explainer, llm, vision (SymPy + AI)
│   ├── routers/       # auth, problems, vision
│   ├── alembic/       # DB migrations
│   └── credentials/   # (gitignored) Vertex AI service account
├── web/               # Next.js frontend
│   └── src/
│       ├── app/       # pages: /, /login, /signup, /practice, /history, /stats
│       ├── components/# Canvas, Navbar, QuestionCard, AuthGuard
│       ├── context/   # AuthContext (JWT in localStorage)
│       └── lib/       # api.ts (typed API client + auto-refresh)
├── docker-compose.yml # postgres + redis + backend + web
├── README.md
└── SETUP.md
```

---

## API overview

Interactive docs: `http://localhost:8016/docs`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | – | Create account → `{user, access_token, refresh_token}` |
| POST | `/auth/login` | – | Login → tokens |
| POST | `/auth/refresh` | – | Rotate tokens with a refresh token |
| GET | `/auth/me` | ✅ | Current user |
| POST | `/problems/generate` | ✅ | Generate + persist a question (`templates` or `gemini`) |
| POST | `/problems/grade` | ✅ | Grade an answer; auto-explains on wrong answers |
| POST | `/problems/explain` | ✅ | Manual step-by-step explanation |
| GET | `/problems/{id}` | ✅ | Question + stored solution steps |
| POST | `/vision/detect` | ✅ | Transcribe a handwritten canvas image (base64) |
| GET | `/attempts` | ✅ | Per-user attempt history |
| GET | `/stats` | ✅ | Accuracy + per-topic breakdown |

A ready-to-import **Postman collection** lives in the repo root: `bacii-math.postman_collection.json`.

---

## Status

**Done**
- Full auth (signup / login / refresh / JWT rotation)
- Complex-number question generation (SymPy templates + Gemini variety), grading (exact + tolerance), step-by-step explanations
- Handwriting detection (local Ollama) with preprocessing
- Persistence (users, questions, steps, attempts, explanations) + history & stats
- Everything containerized; web app with canvas + upload + typed-answer input

**Next**
- More BAC II topics (integrals, probability, geometry, differential equations, conics, functions)
- Question-type selector in the UI per topic
- Production build of the web app (multi-stage Docker image)
- Deployment
