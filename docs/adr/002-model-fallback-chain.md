# ADR 002: Gemini → Ollama → Deterministic Fallback Chain

## Context

Two user-facing features depend on an LLM producing free-text output on top of SymPy's exact math:
narrating solution steps in plain language (English or Khmer), and commenting on a student's
handwritten work. Handwriting OCR (turning a canvas image into math text) has a similar shape: a
model reads an image and returns structured text. Any single LLM call can fail — network issues,
provider outage, a missing/misconfigured cloud credential, or a per-user rate limit — and the
product still needs to respond to the student in that moment.

## Decision

LLM-backed features go through a fixed fallback order, implemented once in
`engine/llm.py`'s `_generate_with_fallback` and mirrored for vision OCR in `engine/vision.py`:
1. **Gemini via Vertex AI** (cloud, primary) — gated by a per-user rate limit
   (`cache.allow_gemini`, default 10/min) so a single user can't exhaust the shared quota.
2. **Local Ollama** (runs on the host machine, reached via `host.docker.internal:11434`) — used
   when Gemini is disallowed, unconfigured, or its call fails.
3. **Deterministic SymPy-derived text** (`engine/explainer.py`) — a plain rendering of the
   solver's own steps, with no LLM involved at all, used when neither model returns anything.

Vision OCR follows the same shape via `VISION_PROVIDER=gemini|ollama|fallback`. Gemini
explanations are cached in Redis (keyed by topic/question/params) so an identical question is
never re-billed to regenerate the same narration.

## Consequences

- The app degrades rather than breaking: a Gemini outage or an unset service-account credential
  still leaves the student with *something* — worse, but not silence or an error page.
- The per-user rate limit bounds Gemini/Vertex spend without a hard outage when it's hit; the
  student is simply served from a cheaper tier instead.
- Explanation caching further reduces repeat Gemini billing for the same generated question.
- Response quality is uneven across the chain: deterministic fallback text is materially plainer
  than an LLM narration, so two students hitting the same feature can get visibly different
  experiences depending on provider availability.
- Two model stacks to operate: a paid cloud service (Vertex AI) and a self-hosted model (Ollama on
  the host), each with its own setup, monitoring, and failure modes.
- Local Ollama output depends on the host machine's installed model and hardware, so behavior can
  differ between a developer's machine, staging, and production in ways cloud-only wouldn't.

## Alternatives considered

- **Gemini only, fail hard when unavailable**: rejected — there is no code path that surfaces "no
  explanation available" to the student; a deterministic explainer always exists as the floor.
- **A second cloud LLM provider as fallback** instead of local Ollama: not what was built. Ollama
  was chosen for the middle tier instead of, say, another hosted API — the reasoning isn't
  recorded in code.
- **No narration at all, just raw SymPy steps**: rejected implicitly, since narration is the
  primary way steps are shown to students; raw steps are the explicit deterministic fallback, not
  the intended default experience.

## TODO(founder)

- Why Ollama specifically as the middle tier rather than a second cloud provider — cost, data
  locality/privacy for Cambodian student data, or resilience to unreliable classroom internet?
- Is the deterministic (no-LLM) explanation considered acceptable long-term UX for a portion of
  traffic, or strictly an emergency stopgap that should trigger an alert when it's hit?
- Is there monitoring today for how often each tier is actually served, and what's the acceptable
  threshold before it's treated as an incident?
- Is the 10/min per-user Gemini rate limit a deliberate cost/business number, or a placeholder
  that hasn't been revisited?
