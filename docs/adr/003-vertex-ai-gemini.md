# ADR 003: Google Gemini via Vertex AI as the Primary Model Provider

## Context

The product needs two AI-adjacent capabilities beyond the SymPy math core (see
[ADR 001](001-sympy-for-computation.md)): turning a solver's steps into natural-language
explanations — in both English and authentic Khmer — and reading a student's handwritten math work
from a canvas image (OCR). It also generates structured, locked-value Khmer reference solutions
via tool/function calling, where the model must fill in prose without ever being allowed to alter
a number. All three currently run on Google's Gemini models accessed through Vertex AI, using one
GCP service account (`backend/credentials/gemini-service-account.json`) shared by both the text
and vision paths.

## Decision

Gemini via Vertex AI is the default provider for narration, work-checking commentary, Khmer
solution generation, and handwriting OCR (`VISION_PROVIDER=gemini` by default). A single service
account authenticates all of it. Model names are configurable (`gemini_model`,
`gemini_vision_model`) and can be changed at runtime through admin-controlled system settings
without a redeploy. Local Ollama exists as an explicit fallback/alternative for text and vision
(see [ADR 002](002-model-fallback-chain.md)), not as the primary.

## Consequences

- One vendor and one credential cover both text and vision, simplifying integration compared to
  running separate OCR and text-LLM providers.
- Vertex AI's structured output / function-calling is used to keep math values locked while the
  model only fills in Khmer prose (`narrate_km_solution`'s tool schema) — a reliability property
  a plain text completion would need extra parsing/validation to approximate.
- Gemini's multilingual capability is load-bearing: prompts explicitly require "100% authentic
  Khmer, no English words," which the target audience (Cambodian BAC II students) requires.
  Switching to a model with weaker Khmer would be a user-facing regression, not just a swap.
  Whether this was benchmarked against alternatives before choosing Gemini is unclear.
- Runtime-swappable model names let the team tune cost/quality/latency without redeploying.
- Introduces a real dependency on Google Cloud: billing, quota, and a correctly provisioned
  service account. A misconfigured or revoked credential silently degrades every Gemini-backed
  feature to the Ollama/deterministic fallback rather than failing loudly, which is good for
  resilience but can mask an operational problem for a while.
- Per-call cost/latency/token usage is already tracked (`record_api_usage`), suggesting Gemini
  spend and reliability are treated as things worth watching from early on.
- Student handwriting images and answers are sent to a third-party cloud vision API. For an
  education product whose users are likely minors, this carries privacy/compliance weight that
  isn't visible from the code alone.

## Alternatives considered

- **OpenAI (GPT-4/GPT-4V) or another hosted multimodal API**: no trace in the codebase — not
  evidently evaluated, or evaluated outside the repo.
- **Local vision-language model as primary** (Ollama `qwen2.5vl:3b`, already integrated): built
  and available, but demoted to fallback/optional rather than default. CLAUDE.md describes OCR as
  "cloud-first but optional-local," which reads as Gemini vision being judged more accurate or
  more reliable than the local model for this handwriting-recognition task — but no benchmark or
  comparison lives in the repo to confirm that.
- **Other cloud vendors (Azure, AWS) for multimodal**: no evidence either was considered.

## TODO(founder)

- Why Gemini specifically over OpenAI or Anthropic for this — cost, measured Khmer-language
  quality, an existing Google Cloud relationship/credits, latency, or something else?
- Is there a data processing agreement with Google covering student data — especially minors' — for
  Cambodia specifically? What does the privacy story look like if asked by a school, examiner, or
  investor?
- Was Gemini vision's OCR accuracy actually benchmarked against the local Ollama `qwen2.5vl` model
  before making Gemini the default, or is the choice provisional?
- If Vertex AI pricing, availability, or terms change materially, is multi-cloud redundancy a
  planned mitigation, or is the Google dependency considered acceptable long-term?
