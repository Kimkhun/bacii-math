# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

BACII Math Practice — students handwrite answers to Cambodian BAC II math problems and get instant,
mathematically-exact grading plus step-by-step explanations. Current topic: Complex Numbers (modulus,
argument, conjugate, real/imaginary parts); architecture is meant to extend to other BAC II topics later.

**Core principles that constrain design decisions:**
- **SymPy is the source of truth.** Answers and grading are always computed by SymPy (each topic's
  `engine/topics/<topic>/solver.py`, plus the generic grading core in `engine/core/grading.py`), never by
  an LLM. Never let an LLM compute or validate a math answer directly.
- **LLMs only narrate and propose.** Gemini (Vertex AI) → Ollama → deterministic SymPy text is the fallback
  chain for turning SymPy's steps into friendly explanations. In Gemini generation mode, the LLM proposes a
  problem but SymPy still recomputes/validates the answer before it's accepted (`engine/topics/complex/generator.py`).
- **Handwriting OCR is cloud-first but optional-local.** Default OCR provider is Gemini vision via
  Vertex AI (the same service account used for explanations). Local Ollama on the host remains available
  as an alternative or fallback via `VISION_PROVIDER=ollama|gemini|fallback` (`engine/vision.py`).

## Running the stack

Full stack (Postgres, Redis, backend, web) via Docker Compose:
```bash
docker compose up -d --build
# Web:      http://localhost:3016
# API docs: http://localhost:8016/docs
```

Prerequisite for **Gemini OCR** (default): a Vertex AI service account at
`backend/credentials/gemini-service-account.json` (same one used for explanations).

Prerequisite for **local OCR** (`VISION_PROVIDER=ollama`): Ollama running on the **host** (containers reach
it via `host.docker.internal:11434`), with `ollama pull qwen2.5vl:3b` (vision OCR) and optionally
`qwen2.5:3b` (text fallback).

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
                                                       rate-lim) vision)  vision +
                                                                    explanations)
```

### Backend layout (`backend/`)
- `main.py` — FastAPI app, CORS, router registration.
- `routers/` — thin HTTP layer (`auth.py`, `problems.py`, `profile.py`, `vision.py`); delegates to `services.py`.
  `profile.py` serves the student profile (`/profile`, `/profile/rebuild`, `/skills`) — skill level,
  per-topic progress and practice suggestions; see "Skill progress" below.
  `problems.py` also exposes past-exam replay (`GET /problems/exam/{exam_id}`,
  `POST /problems/exam/{exam_id}/submit`) and, under `me_router`, formula/template introspection
  endpoints (`/me/formulas`, `/me/templates`, `/me/templates/structures`, `/me/templates/summary`,
  `/me/templates/structures/regenerate`) used by the web `/admin` page; `/me/formulas` is separate
  and student-facing (used by `/formulas` and `/practice` too). The template endpoints are gated by
  `get_current_admin_user` (`core/deps.py`), which requires `User.is_admin`. There is no signup path
  or promotion endpoint for admin — the single admin account is upserted from `ADMIN_EMAIL`/
  `ADMIN_PASSWORD` env vars on every backend startup (`main.py`'s `seed_admin_user`).
- `services.py` — orchestration layer: wires `engine/` + `models.py` + `cache.py` together for each
  endpoint's use case (create question, grade, explain, stats, exam replay, template introspection,
  skill tracking + profile). This is the place to look first to understand a request's full flow.
- `engine/` — the math/AI core, framework-agnostic, organized **by topic**:
  - `solver.py` / `generator.py` / `grader.py` — thin public facade modules (do not rename); each
    re-exports the real implementation from `engine/core/` and `engine/topics/<topic>/`.
  - `core/` — the topic-neutral kernel: `dispatch.py` (routes `solve()`/`generate()` to the right
    topic), `grading.py` (`parse_answer`/`analyze_work`/`grade`/`grade_part` + every generic
    answer-kind judge — compares a user answer against the SymPy-exact answer, exact or
    tolerance-based), `rubric.py` (deterministic step-by-step points rubric for generated/live
    questions of any topic — derives per-checkpoint point weights mechanically from the same
    `checkpoints` list `solve()` already returns, so no topic hand-lists point values), `shared.py`
    (question-type registry + small SymPy formatting helpers), `slots.py`/`expr_shared.py`
    (template-filling helpers shared by the limit/integral generators), `skills.py` (the skill
    taxonomy — one leaf per practisable exercise type, derived from the generators' own registries),
    `mastery.py` (the 0-100 skill-level math: recency-weighted rate + time-decayed evidence) and
    `coaching.py` (the deterministic "what to practise next" rules).
  - `topics/<topic>/` — one self-contained folder per BAC II topic (`complex`, `limit`, `integral`,
    `probability`, `functions`, `continuity`, `derivatives`, `differential_equations`,
    `vectors_space`, `conics`, `past_exam`), each with its own `solver.py` (SymPy computation of
    exact answers + solution steps), `generator.py` (builds problems either from integer templates —
    `generation_mode="templates"`, keeps answers clean — or via Gemini proposal re-validated by
    SymPy for `generation_mode="gemini"`, complex-topic only), `grader.py` (topic-specific grading
    rules, when any differ from the generic core), and `data/` (curated real-exam exercises +
    formula-sheet JSON). Probability's scenario catalog lives at
    `engine/topics/probability/scenarios.py` + `data/scenarios/*.json`: sampled slots →
    constraint-validated → filled Khmer sentence → SymPy-solved (no LLM in v1 generation).
    `past_exam` is a special topic backing full past-exam replay (`backend/data/past_exams/*.json`,
    e.g. the 2018 exam): its own `rubric.py` hand-lists each question's graded steps in the teacher's
    printed order (mirroring the paper's layout) and derives point weights from them with the same
    two rules as `core/rubric.py`, rather than reusing the generic solver-checkpoint-derived rubric.
    See `docs/engine-layout.md` for the full file map and the "add a topic" recipe, and
    `docs/README.md` for the full documentation index (pipeline, step-checking, canvas, exam-data,
    generator variants, etc.).
  - `explainer.py` — turns solver steps into deterministic plain-text explanation (LLM fallback baseline).
  - `llm.py` — Gemini (Vertex AI) client (text + vision) + Ollama text/vision calls, with the
    Gemini → Ollama → deterministic fallback chain and rate-limiting via `cache.allow_gemini`.
  - `vision.py` — image preprocessing (auto-crop to ink, upscale) and OCR provider dispatch
    (`VISION_PROVIDER=gemini|ollama|fallback`). Returns plain-text `lines` (fed to `analyze_work`
    and the LLM), `lines_latex` (display-only LaTeX, rendered with KaTeX in the web UI), the
    extracted final answer, and a `provider` field.
- `models.py` — SQLAlchemy 2.0 async models: `User`, `Question`, `Step`, `Attempt`, `Explanation`,
  `StudySession`, `SkillState` (the per-student skill/formula mastery tracker).
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

### Rubric-based (points) grading
Alongside pass/fail step grading, `engine/core/rubric.py` and `engine/topics/past_exam/rubric.py`
compute a deterministic points breakdown per question/exam (used by the exam-replay flow). Both derive
point weights mechanically from an ordered list of graded steps — the last step of a part/item gets 40%
of that part's points, the rest split the remaining 60% evenly — rather than hand-typing point values;
they differ only in where that step list comes from (the generic solver's `checkpoints` vs. a
hand-listed order matching the printed exam paper). See the module docstrings for the full rationale.

### Skill progress & practice suggestions
Every graded attempt also updates two hidden trackers (`SkillState` rows): one for the **exercise
type** the question belongs to (a leaf skill from `engine/core/skills.py` — "sin(x)/x limits", not
"limits") and one per **formula** the step-checker watched. `engine/core/mastery.py` turns those into
a 0-100 level (recency-weighted success rate x time-decayed evidence, shrunk toward a pessimistic
prior, so the bar fills only once a skill is repeatedly *shown*), and `engine/core/coaching.py` ranks
what to practise next — including the case that matters most, a technique sitting far below its own
topic ("your Limits score is 52, but sin(x)/x sits at 26"). `GET /profile` assembles all of it.
The tracker is replayable: `rebuild_skill_states` replays stored attempts and reproduces exactly what
live recording wrote, so changing `mastery.TRACKER_VERSION` re-derives everything with no migration.
Full design: `docs/skill-progress.md`.

### Web layout (`web/src/`)
- `app/` — Next.js App Router pages: `/`, `/login`, `/signup`, `/practice`, `/history`, `/stats`,
  `/profile` (skill level, per-topic progress bars, practice suggestions),
  `/formulas`, `/exam` (past-exam replay, points-rubric results), `/admin` (formula/template
  inventory and structure regeneration, admin-only both client-side via `AdminGuard` and
  server-side via the `me_router` template endpoints above).
- `components/` — `Canvas` (handwriting capture), `QuestionCard`, `Navbar`, `AuthGuard`.
- `context/AuthContext.tsx` — JWT stored in `localStorage`, exposes auth state to the app.
- `lib/api.ts` — typed API client; auto-refreshes the access token on a 401 using the refresh token.

### Handwriting detection flow
Canvas/upload image (base64) → `POST /vision/detect` → backend preprocesses (auto-crop + upscale,
`engine/vision.py`) → OCR via the configured provider (Gemini Vertex vision by default, or Ollama
`qwen2.5vl:3b`) returns `{lines, lines_latex, raw_text, latex, tokens, confidence, provider}` → the
plain `lines` are submitted to `POST /problems/grade` (graded by SymPy; `lines_latex` is display-only
and rendered with KaTeX in the web UI). If `lines` can't be parsed into a verified step-check, the AI
work-check is skipped and a deterministic "couldn't read your steps" message is shown instead.

## Configuration

Backend settings (`backend/core/config.py`, overridable via env vars or `backend/.env`): `database_url`,
`redis_url`, `jwt_secret`, `gemini_model`/`gemini_vision_model`/`gemini_location`, `ollama_url`,
`vision_model`, `text_model`, `vision_provider` (`gemini` default, `ollama`, or `fallback`),
`gemini_rate_limit_per_minute`, `explanation_cache_ttl_seconds`. In Docker Compose these are injected
directly as environment variables (see `docker-compose.yml`); `GOOGLE_APPLICATION_CREDENTIALS` points at
a mounted `backend/credentials/gemini-service-account.json` (gitignored).

Web reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8016`).

## Adding a new topic

Each BAC II topic is a self-contained folder under `engine/topics/<topic>/`. Add a new one by writing
`solver.py` (the topic's SymPy computation), `generator.py` (template/Gemini generation), and `grader.py`
(only needed if grading differs from the generic core in `engine/core/grading.py`) — then register the
topic + its question types in `engine/core/shared.py` and `engine/core/dispatch.py`. `services.py` and the
routers are already topic-agnostic (topic is just a field on `Question`), and the profile picks the topic
up automatically — but if the topic has a sub-technique axis worth tracking separately, teach
`engine/core/skills.py` how to enumerate it and how to read it back out of `params`. Full recipe:
`docs/engine-layout.md` and `docs/adding-question-types.md`.
