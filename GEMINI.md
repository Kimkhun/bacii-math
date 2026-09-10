# 🤖 Antigravity AI Working Rules & Architectural Protocol

> **CRITICAL BEHAVIORAL RULE**: 
> You MUST ALWAYS plan, discuss, and explain your approach FIRST before modifying, creating, or deleting files. 
> DO NOT write code, launch unprompted subagents, or commit without explicit confirmation and approval from the USER.
> Code what the USER wants, not what you assume they want. Always verify intent first.

---

## 1. 🛑 Mandatory "Plan First, Approve First" Workflow
Before writing code or executing non-read operations:
1. **Analyze & Formulate Plan**: Break down the task into clear, numbered steps.
2. **Present to User**: Explain what you plan to do, why, and highlight any trade-offs or design decisions in plain language (no raw unreadable math syntax).
3. **Wait for Explicit Approval**: Ask the user for confirmation. Only proceed to file edits once the user confirms.
4. **User Has the Final Say**: Suggest improvements and best practices, but never enforce them autonomously. The user always decides.
5. **No Blind Fast Commits**: Only commit to git when the user explicitly requests it or agrees on the milestone.
6. **No Blind Deletions or Scorched-Earth Reverts**: NEVER delete, wipe, or revert entire features or files without explicitly asking the user WHAT specific scope or revision they want reverted. If the user says "revert", confirm the exact milestone/changes first before touching files.

---

## 2. 🏗️ Tech Stack & Microservices Architecture (BAC II Math)
* **Frontend Web App (`web/`)**:
  - Next.js 14 (App Router) + TypeScript + Tailwind CSS on port `3016` (container: `bacii-web-1`).
  - KaTeX for mathematical equation rendering.
  - Virtual Canvas with custom pointer events for pen, stylus, touch, and mouse input.
* **Backend Engine (`backend/`)**:
  - FastAPI (Python 3.12) on port `8016` (container: `bacii-backend-1`).
  - **SymPy 1.13**: Deterministic computer algebra system for all problem generation, solving, and line-by-line verification.
  - **Google Gemini API**: Used strictly for handwriting OCR, visual hand-drawn graph grading, and authentic Khmer step narration.
* **Datastore & Cache**:
  - PostgreSQL 16 on port `5432` (`bacii-postgres-1`).
  - Redis 7 on port `6379` (`bacii-redis-1`) for fast session caching and Gemini explanation caching.

---

## 3. 🎨 UI, Typography & UX Ground Rules
* **Khmer vs. KaTeX Segregation**:
  - NEVER wrap raw Khmer sentences inside `\text{...}` within KaTeX math mode (this causes font bounding box failures, missing glyphs, and raw bracket leaks).
  - Use `latexToMixedText`: render Khmer words using native browser typography, and isolate mathematical symbols inside `$...$` for KaTeX rendering.
* **Clean Tabs & Navigation**:
  - Number tabs with clean English digits (`1`, `2`, `3`, `4`) or question letters (`A`, `B`, `C`, `D`).
  - NEVER show confusing sub-step tags (`1.a`, `1.b`, `Sub-step:`) in the primary student UI. Sub-steps are graded progressively behind the scenes.
* **Full Problem Statement Visibility**:
  - Do NOT slice exam questions into isolated fragments that hide the preamble.
  - Keep the problem preamble and all numbered questions visible in the top header.
  - Highlight the active tab's question with the amber accent card (`bg-amber-50 border-amber-500`).
* **Tablet & Stylus Ergonomics**:
  - Differentiate pointer types via `e.pointerType` (`pen`, `touch`, `mouse`).
  - Support pen hover indicators, pressure-sensitive stroke smoothing, and palm rejection (ignore touch drawing when stylus is active).

---

## 4. 📐 Mathematical Engine & Grading Integrity
* **SymPy Is Ground Truth**:
  - Ground-truth answers and intermediate checkpoints MUST be computed deterministically using SymPy, never generative LLM arithmetic.
* **Sequential Line-by-Line Checking**:
  - `analyze_work` checks each written line against step-by-step checkpoints.
  - Lines equivalent to prior checkpoints must be accepted as valid restatements (never flag repeated correct values as wrong).
* **Authentic Cambodian BAC II Notation**:
  - Recognize domain symbols (e.g., $g$ ជាអនុគមន៍កើនលើ $D$ / ដែន satisfies monotonicity).
  - Support both radical conjugate expansions when both numerator and denominator contain square roots.
* **Dynamic Templates vs. Curated Pools**:
  - True templates vary parameters cleanly (e.g. Pythagorean triples for complex modulus, clean integer roots for limits).
  - Never emit raw Python code strings (such as `**`, `*`, or `exp()`) directly into student problem statements; always pretty-print or convert to clean LaTeX.

---

## 5. 🐳 Docker & Verification Commands
Always test changes inside the running containers before declaring work complete:

```bash
# Check running containers
docker ps --format "{{.Names}} \t {{.Status}}"

# Check web container build logs
docker logs bacii-web-1 --tail 30

# Check backend container logs
docker logs bacii-backend-1 --tail 30

# Run quick engine verification inside backend
docker exec bacii-backend-1 python -c "from engine.core.dispatch import generate, solve; import asyncio; print('Backend OK')"
```

---

## 6. 🌿 Git & Collaboration Rules
* **No Unverified Commits**: Run the topic regression checks before committing.
* **Clear Commit Messages**: Use standard semantic conventions (`feat:`, `fix:`, `refactor:`, `docs:`).
* **Respect Collaborator Branches**: Ensure compatibility with collaborator changes (e.g. Joel's canvas drag/paste enhancements) and never overwrite work without checking git log.
