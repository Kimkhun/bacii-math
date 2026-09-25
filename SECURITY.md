# Security Audit & Remediation

Date: 2026-09-25
Scope: full-stack audit of `main` (backend FastAPI service, Next.js web app,
Docker deployment, dependencies, and git history) at commit `f150487`.

This document lists every issue found and the fix applied. Exploit specifics are
described at the level needed to understand the risk, not as reproduction
recipes. Items marked **Operator action** need a configuration change at deploy
time in addition to the code fix.

## Summary

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | Critical | Student answers evaluated as arbitrary code in the answer parser | Fixed |
| 2 | High | A tiny answer can pin CPU/RAM in the CAS (denial of service) | Fixed (mitigated) |
| 3 | High | Guessable default secrets shipped in deploy config | Fixed + operator action |
| 4 | High | Postgres & Redis published on all network interfaces | Fixed |
| 5 | High | Unbounded paid-LLM calls (OCR, hints, generation) — cost abuse | Fixed |
| 6 | Critical (dependency) | Vulnerable Next.js version | Fixed (patch); one transitive residual |
| 7 | Medium | No brute-force protection on auth; password hashing blocks the event loop | Fixed |
| 8 | Medium | Tokens could not be revoked | Fixed |
| 9 | Medium | Admin seeding could over-grant and never demoted | Fixed |
| 10 | Medium | Image decompression bomb in OCR upload | Fixed |
| 11 | Medium | No size limits on submitted text (DB flooding) | Fixed |
| 12 | Medium | Containers ran as root; dev servers in deploy config | Fixed (hardening) + operator note |
| 13 | Low | Internal error text leaked to clients (vision endpoint) | Fixed |
| 14 | Low | Weak/absent signup validation | Fixed |
| 15 | Low | CORS allow-list contained a hard-coded LAN IP | Fixed |
| 16 | Low | Unpinned Python dependencies | Documented |

---

## Critical

### 1. Arbitrary code execution via the answer parser

**Where:** `backend/engine/core/grading.py` — `parse_answer` (used by
`/problems/grade`, `/problems/explain`, `/problems/hint`, and
`/problems/exam/{id}/submit`, plus every handwriting submission, since OCR text
is fed into the same parser).

**Risk:** `parse_answer` passed user-supplied text to SymPy's `parse_expr`, which
compiles and evaluates the string as a Python expression. Ordinary Python
expression syntax (attribute access on built-in objects) reaches the interpreter
object graph — i.e. a logged-in student could run code in the backend process,
not just do math. Signup is open, so any anonymous person could obtain an
account and reach this. This is the most serious finding: it exposes the Vertex
AI service-account key, `JWT_SECRET`, and the database.

**Fix:** Added an allow-list style guard, `_reject_unsafe_expr`, run on every
user string before it reaches the evaluating parser (`_safe_parse_expr`). Real
BAC II answers only ever need digits, the operators `+ - * / ^`, function calls,
symbols, and decimal points — none of which require attribute access, dunder
names, or `lambda`. The guard rejects:
- dunder tokens (`__…__`),
- attribute access (a `.` touching a name; a decimal point between digits is not
  matched, so `0.5` still parses),
- `lambda`,
- and over-long input (see #2).

Both the primary parse and the "retry with the right-hand side of `=`" fallback
now go through the guard. Verified: legitimate answers (fractions, radicals,
complex numbers, limits, ODE constants, degree/radian units, the `AB.AC=36`
dot-product echo) still parse; code-injection shapes are rejected as
"unsupported syntax" before evaluation.

---

## High

### 2. CAS denial-of-service via crafted answers

**Where:** same parser as #1.

**Risk:** A short input describing a *nested* power (a power whose exponent is
itself a power) expands to an astronomically large integer, freezing a CPU core
for minutes and/or exhausting memory. The existing 45-second thread timeout only
stops the request from *waiting* — the worker thread keeps computing, so a few
such requests could starve the whole service.

**Fix:** `_reject_unsafe_expr` also rejects nested exponentiation
(`a^b^c` / `a**b**c`), single powers with very large literal exponents, and
input longer than 512 characters — none of which is a real answer. Verified: the
previously-hanging inputs now return an immediate parse rejection.

**Further hardening (not yet done):** truly bounding runaway computation needs a
*killable* worker process rather than a thread (noted in `core/offload.py`).
The guard removes the cheap, obvious triggers.

### 3. Guessable default secrets in deploy config

**Where:** `docker-compose.yml`, `.env.example`.

**Risk:** `JWT_SECRET` defaulted to `dev-secret-change-me` (forgeable auth
tokens for any user), the admin account defaulted to a published password, and
the Postgres password defaulted to `postgres`. Any deployment that didn't
override them was trivially compromised.

**Fix:** Added an `ENVIRONMENT` setting and a startup guard
(`core/security.assert_secure`, called in `main.py`) that **refuses to boot when
`ENVIRONMENT=production` and any of `JWT_SECRET` / `ADMIN_PASSWORD` / the
Postgres password is still a known dev default.** Compose now passes
`ENVIRONMENT` through, and both `.env.example` files document the requirement.
Working dev defaults are retained so a fresh clone still runs locally.

**Operator action:** set `ENVIRONMENT=production` and strong values for
`JWT_SECRET`, `ADMIN_PASSWORD`, and the Postgres password before deploying.

### 4. Postgres and Redis exposed on all interfaces

**Where:** `docker-compose.yml`.

**Risk:** Both data stores published their ports on every interface, and Redis
has no password. Anyone able to reach Redis could rewrite the active model
configuration, poison the shared explanation/solution cache served to all
students, or reset rate-limit counters.

**Fix:** Both port mappings are now bound to `127.0.0.1` only. The backend
reaches them over the Compose network, so no external exposure is needed.

**Operator note:** if the data stores must run on a separate host, put them on a
private network and add a Redis password rather than re-publishing the ports.

### 5. Unbounded paid-LLM calls (cost abuse)

**Where:** `backend/engine/vision.py` (OCR), `backend/engine/hints.py` +
`services.hint_question`, `services.create_question` (Gemini generation mode).

**Risk:** Three paid Vertex AI paths ignored the per-user Gemini rate limit that
already guards explanations, so a scripted client could run up an unbounded
bill.

**Fix:** All three now consult `cache.allow_gemini` before making a billed call:
- OCR: the cloud-only `gemini` provider returns a `rate_limited` result when the
  budget is spent; the `fallback` provider still uses local Ollama first.
- Hints: `allow_gemini` is threaded from the service into `generate_hint`.
- Gemini generation mode: falls back to free SymPy template generation when the
  budget is spent.

### 6. Vulnerable Next.js version (dependency)

**Where:** `web/package.json`, `web/package-lock.json`.

**Risk:** The pinned `next@^15.1.6` resolved to a version with published
advisories, including a critical image-optimization RCE and high-severity issues
inherited via `sharp` and `postcss`.

**Fix:** Bumped to `next@15.5.26` (regenerated `package-lock.json`), which clears
the critical Next.js RCE and the `sharp` advisory. The web app does not use
`next/image`, but the upgrade is applied regardless.

**Residual (documented, low real-world risk):** one `postcss` advisory remains,
pinned transitively inside Next's own build tooling. `npm` can only clear it by
force-upgrading to `next@16` — a breaking major upgrade that warrants its own
tested migration. The affected `postcss` code path processes the app's own
Tailwind CSS, not user input, so exposure here is low. Track the Next 16 upgrade
separately.

Note: `web/.npmrc` points npm at a third-party mirror and disables `audit`,
which is why these advisories never surfaced in CI. Consider running
`npm audit` against the public registry in CI.

---

## Medium

### 7. No brute-force protection; password hashing on the event loop

**Where:** `backend/routers/auth.py`, `backend/cache.py`.

**Risk:** `/auth/login` and `/auth/signup` had no attempt throttling, enabling
online password guessing. Separately, bcrypt (deliberately slow, CPU-bound) ran
directly in the async handler, so a burst of logins stalled every other request.

**Fix:**
- Added `cache.auth_rate_limit`, a fixed-window limiter keyed by both client IP
  and target email, applied to login and signup. It fails **open** if Redis is
  down so a cache outage can't lock everyone out.
- bcrypt `hash_password` / `verify_password` now run in a worker thread
  (`run_in_thread`), keeping the event loop responsive.

### 8. Tokens could not be revoked

**Where:** `backend/core/security.py`, `backend/core/deps.py`,
`backend/routers/auth.py`, `backend/models.py`, new migration
`b8d3f1a2c4e6_add_token_version_to_users.py`.

**Risk:** `/auth/refresh` minted fresh token pairs indefinitely; there was no way
to invalidate a leaked token.

**Fix:** Added a `token_version` column to `User`. Every access/refresh token now
carries a `ver` claim, checked on authentication and on refresh; incrementing a
user's `token_version` invalidates all of their outstanding tokens
(logout-everywhere / forced re-auth / password reset). The mechanism is now in
place for future password-change and logout endpoints to use.

### 9. Admin seeding could over-grant and never demoted

**Where:** `backend/main.py` (`seed_admin_user`).

**Risk:** Seeding upserted the configured admin but never removed admin rights
from anyone else, so rotating `ADMIN_EMAIL` left the previous admin privileged.

**Fix:** Startup now strips `is_admin` from every account except the currently
configured admin email, enforcing the "exactly one admin" invariant.

**Operator note:** pointing `ADMIN_EMAIL` at an address that a user already
registered will, by design, promote that account on the next boot — treat
`ADMIN_EMAIL` as a sensitive setting.

### 10. Image decompression bomb in OCR

**Where:** `backend/engine/vision.py`.

**Risk:** A tiny, highly-compressed PNG can decode to hundreds of millions of
pixels; the OCR pipeline decoded the image (and copies of it) fully into memory,
so one crafted upload under the byte-size cap could exhaust RAM.

**Fix:** Set `Image.MAX_IMAGE_PIXELS = 25_000_000` (far above any real canvas
export, well under Pillow's default), so oversized images are refused during
decode.

### 11. No size limits on submitted text

**Where:** `backend/schemas.py`.

**Risk:** `user_answer`, `work_text`, `strokes_thumb`, exam answers, and saved
progress were stored with no length cap, allowing database flooding.

**Fix:** Added `max_length` bounds to the relevant request fields across
`GradeRequest`, `ExplainRequest`, `HintRequest`, `GradeGraphRequest`,
`SaveProgressRequest`, and a size validator on `ExamSubmitRequest`.

### 12. Containers ran as root; dev servers in deploy config

**Where:** `backend/Dockerfile`, `web/Dockerfile`, `docker-compose.yml`.

**Risk:** Both images ran as root, widening the blast radius of any container
compromise. The Compose file also runs the backend with `uvicorn --reload` and
the web app with `next dev`, mounting source into the containers — appropriate
for development, not production.

**Fix:** Both Dockerfiles now create/use an unprivileged user.

**Operator note:** the provided `docker-compose.yml` is a development
configuration (hot-reload + source mounts). For production, run the backend
without `--reload`, build the web app (`next build` / `next start`), and drop the
source bind-mounts.

---

## Low

### 13. Internal error text leaked to clients

**Where:** `backend/routers/vision.py` — the `/vision/detect` handler returned
raw exception text in its 502 response. It now logs the detail server-side and
returns a generic message.

### 14. Weak/absent signup validation

**Where:** `backend/schemas.py` — signup accepted any string as an email and any
password (including empty). Now enforces a basic email shape and an 8–128
character password. `core/security` also clips passwords to bcrypt's 72-byte
limit so an over-long password is a normal mismatch rather than a 500 error.

### 15. CORS allow-list contained a hard-coded LAN IP

**Where:** `backend/main.py`, `backend/core/config.py` — the credentialed CORS
allow-list hard-coded a private LAN IP. Origins are now driven by a
`CORS_ORIGINS` setting (local-dev origins by default); set it explicitly in
production.

### 16. Unpinned Python dependencies

**Where:** `backend/requirements.txt` — most packages have no version pin, so
builds aren't reproducible and can't be audited against known-vulnerable
versions. Recommendation: pin to tested versions (and add a Python dependency
scan such as `pip-audit` to CI). Left unpinned here to avoid guessing versions
that might break the build.

---

## Reviewed and found clean

- **Object ownership (IDOR):** attempts, progress sessions, and the
  attempt-to-explanation link are all correctly scoped to the current user.
- **SQL injection:** all database access goes through the SQLAlchemy ORM with
  bound parameters.
- **Past-exam file loading:** `exam_id` cannot be used to read arbitrary files.
- **XSS:** KaTeX rendering runs with `trust` disabled and `strict: "ignore"`;
  the one `dangerouslySetInnerHTML` in the layout injects a fixed script, and
  `MathText` passes plain text, not HTML.
- **Admin authorization:** every template, sandbox, and `/admin` route requires
  `is_admin` server-side.
- **Git history:** no committed API keys, service-account files, or `.env`
  secrets were found.

## Verification performed

- Guard unit-tested against a battery of legitimate BAC II answer formats
  (all still parse) and code-injection / DoS shapes (all rejected).
- Injection payloads run end-to-end through `grade()` and `analyze_work()`:
  now rejected as unparseable instead of being evaluated; no hang.
- `core.security.assert_secure` confirmed to raise on production defaults and
  pass in development; bcrypt clip/verify round-trip confirmed.
- Request-schema validators confirmed to reject invalid emails, short
  passwords, and oversized submissions.
- Full FastAPI app imports cleanly; Alembic migrations resolve to a single head.
- `next@15.5.26` lockfile re-resolved and re-audited (critical + sharp cleared).
