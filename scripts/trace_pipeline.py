#!/usr/bin/env python3
"""Step-by-step timing trace of the whole "Check my answer" pipeline.

Unlike scripts/trace_grading.py (black-box HTTP), this runs INSIDE the backend
process context: it imports the real backend modules, wraps every stage with a
timer, then calls the same service functions the routers call:

    vision.detect_math()        <- POST /vision/detect
    services.grade_question()   <- POST /problems/grade

Every wrapped call becomes a span in a nested timeline (start offset, total ms,
self ms, indentation = call depth). Covered stages:

  OCR        image preprocess (crop/upscale), provider dispatch, Gemini API call
             (with prompt/output/thinking token counts), JSON parse/finalize
  grading    SymPy solve, parse/grade, analyze_work (step check), rubric score
  feedback   explanation cache lookup, rate-limit check, narrate LLM,
             check_work LLM, rubric-feedback LLM, deterministic steps text
  persist    every DB get/execute/flush/commit, skill-progress update
  LLM        for each call: prompt, raw response, latency, tokens (incl. thoughts)

Not measured (needs a browser): canvas export, image upload, response download,
KaTeX/animation rendering.

Usage (from the repo root, on the host - it re-executes itself in the container):
  python scripts/trace_pipeline.py
  python scripts/trace_pipeline.py --topic integral --lang km
  python scripts/trace_pipeline.py --image my_work.png --scenarios wrong
  python scripts/trace_pipeline.py --scenarios correct,wrong --no-repeat

Output: traces/pipeline-<timestamp>.md (+ the input PNGs).
Side effects: creates a user trace-pipeline@example.test (reused on later runs)
and real Question/Attempt/Explanation rows for it. Nothing is deleted.
"""
import argparse
import asyncio
import contextvars
import inspect
import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

IN_CONTAINER = os.path.exists("/app/services.py")
CONTAINER_OUT = "/tmp/trace_out"


# --------------------------------------------------------------------------- #
# Host mode: copy this script into the backend container and run it there.
# --------------------------------------------------------------------------- #
def run_on_host() -> None:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--container", default="bacii-math-backend-1")
    ap.add_argument("--image")
    known, rest = ap.parse_known_args()
    here = Path(__file__).resolve()
    root = here.parent.parent
    c = known.container

    def sh(*cmd, check=True):
        return subprocess.run(cmd, check=check)

    sh("docker", "exec", c, "rm", "-rf", CONTAINER_OUT)
    sh("docker", "cp", str(here), f"{c}:/tmp/trace_pipeline.py")
    extra = []
    if known.image:
        sh("docker", "cp", known.image, f"{c}:/tmp/trace_input_image")
        extra = ["--image", "/tmp/trace_input_image"]
    proc = subprocess.run(
        ["docker", "exec", "-w", "/app", "-e", "PYTHONPATH=/app", "-e", "PYTHONUNBUFFERED=1",
         c, "python", "/tmp/trace_pipeline.py", *rest, *extra],
    )
    if proc.returncode != 0:
        sys.exit(proc.returncode)
    dest = root / "traces"
    dest.mkdir(exist_ok=True)
    sh("docker", "cp", f"{c}:{CONTAINER_OUT}/.", str(dest))
    print(f"report copied to {dest}/")


if not IN_CONTAINER:
    if __name__ == "__main__":
        run_on_host()
    sys.exit(0)

# --------------------------------------------------------------------------- #
# Container mode (has /app on sys.path via PYTHONPATH)
# --------------------------------------------------------------------------- #
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

SPANS: list["Span"] = []
_STACK: contextvars.ContextVar[tuple] = contextvars.ContextVar("span_stack", default=())
T0 = 0.0


class Span:
    __slots__ = ("name", "depth", "start", "end", "note", "extra", "parent", "children")

    def __init__(self, name, depth, parent, note=""):
        self.name = name
        self.depth = depth
        self.start = time.perf_counter()
        self.end = None
        self.note = note
        self.extra: dict = {}
        self.parent = parent
        self.children: list[Span] = []

    @property
    def ms(self):
        return ((self.end or time.perf_counter()) - self.start) * 1000

    @property
    def self_ms(self):
        return max(0.0, self.ms - sum(c.ms for c in self.children))


SUPPRESS: contextvars.ContextVar[bool] = contextvars.ContextVar("suppress_spans", default=False)


def _begin(name, note=""):
    if SUPPRESS.get():
        # Fire-and-forget background work (the api_usage_logs write) runs off the
        # student's critical path: don't pollute the timeline with it.
        dummy = Span(name, 0, None, note)
        return dummy, _STACK.set(_STACK.get())
    stack = _STACK.get()
    parent = stack[-1] if stack else None
    sp = Span(name, len(stack), parent, note)
    if parent:
        parent.children.append(sp)
    SPANS.append(sp)
    token = _STACK.set(stack + (sp,))
    return sp, token


def _end(sp, token):
    sp.end = time.perf_counter()
    _STACK.reset(token)


def wrap(obj, attr, name, note_fn=None, capture=None):
    """Replace obj.attr with a timing wrapper. capture(span, args, kwargs, result)
    may stash extra data on the span (prompts, tokens, ...)."""
    orig = getattr(obj, attr)
    if getattr(orig, "_traced", False):
        return

    def _note(a, kw):
        try:
            return note_fn(*a, **kw) if note_fn else ""
        except Exception:
            return ""

    if inspect.iscoroutinefunction(orig):
        async def w(*a, **kw):
            sp, tok = _begin(name, _note(a, kw))
            try:
                r = await orig(*a, **kw)
                if capture:
                    capture(sp, a, kw, r)
                return r
            except Exception as exc:
                sp.extra["error"] = f"{type(exc).__name__}: {exc}"[:300]
                raise
            finally:
                _end(sp, tok)
    else:
        def w(*a, **kw):
            sp, tok = _begin(name, _note(a, kw))
            try:
                r = orig(*a, **kw)
                if capture:
                    capture(sp, a, kw, r)
                return r
            except Exception as exc:
                sp.extra["error"] = f"{type(exc).__name__}: {exc}"[:300]
                raise
            finally:
                _end(sp, tok)
    w._traced = True
    w.__name__ = getattr(orig, "__name__", attr)
    setattr(obj, attr, w)


def install_hooks():
    import cache
    from sqlalchemy.ext.asyncio import AsyncSession

    import services
    from engine import explainer, grader, llm, solver, vision

    # ---- OCR -------------------------------------------------------------
    wrap(vision, "_preprocess", "ocr.preprocess (crop+upscale)")
    wrap(vision, "_ollama_generate", "ocr.ollama_call")
    wrap(vision, "_gemini_generate", "ocr.gemini_call",
         capture=lambda sp, a, kw, r: sp.extra.update(raw=r))
    wrap(vision, "_finalize", "ocr.finalize (normalize+map boxes)")
    wrap(vision, "get_system_model_settings", "cache.model_settings")
    wrap(llm, "get_system_model_settings", "cache.model_settings")

    # ---- LLM layer -------------------------------------------------------
    def cap_text(sp, a, kw, r):
        sp.extra["prompt"] = a[0] if a else kw.get("prompt")
        sp.extra["response"] = r if isinstance(r, str) else str(r)

    wrap(llm, "_gemini_generate", "llm.gemini_text (wrapper)", capture=cap_text)
    wrap(llm, "gemini_vision_generate", "llm.gemini_vision (wrapper)",
         capture=lambda sp, a, kw, r: sp.extra.update(prompt=a[0], response=r, image_bytes=len(a[1])))
    wrap(llm, "_ollama_generate", "llm.ollama_text", capture=cap_text)
    wrap(llm, "narrate", "llm.narrate (explanation)")
    wrap(llm, "check_work", "llm.check_work (mistake feedback)")
    wrap(llm, "check_rubric_feedback", "llm.check_rubric_feedback (teacher tip)")

    # Raw Gemini SDK call = pure network + generation time, with token usage.
    try:
        client = llm._gemini_client()
        models = client.aio.models
        orig_gc = models.generate_content

        async def gc(*a, **kw):
            sp, tok = _begin("gemini.api_call", str(kw.get("model", "")))
            try:
                r = await orig_gc(*a, **kw)
                u = getattr(r, "usage_metadata", None)
                if u is not None:
                    sp.extra["usage"] = {
                        "prompt_tokens": getattr(u, "prompt_token_count", None),
                        "output_tokens": getattr(u, "candidates_token_count", None),
                        "thinking_tokens": getattr(u, "thoughts_token_count", None),
                        "total_tokens": getattr(u, "total_token_count", None),
                    }
                    sp.note += (
                        f" in={sp.extra['usage']['prompt_tokens']}"
                        f" out={sp.extra['usage']['output_tokens']}"
                        f" think={sp.extra['usage']['thinking_tokens']}"
                    )
                return r
            except Exception as exc:
                sp.extra["error"] = f"{type(exc).__name__}: {exc}"[:300]
                raise
            finally:
                _end(sp, tok)

        models.generate_content = gc
    except Exception as exc:  # SDK internals changed: keep going without it
        print(f"[warn] could not hook the Gemini SDK call: {exc}")

    # ---- Redis cache -----------------------------------------------------
    def hit(sp, a, kw, r):
        sp.note = "HIT" if r else "MISS"

    wrap(cache, "get_explanation", "cache.get_explanation", capture=hit)
    wrap(cache, "set_explanation", "cache.set_explanation")
    wrap(cache, "allow_gemini", "cache.allow_gemini (rate limit)",
         capture=lambda sp, a, kw, r: setattr(sp, "note", f"allowed={r}"))
    wrap(cache, "get_km_solution", "cache.get_km_solution", capture=hit)

    # ---- SymPy / deterministic engine -----------------------------------
    wrap(solver, "solve", "sympy.solve", note_fn=lambda t, q, *_: f"{t}/{q}")
    wrap(explainer, "build_text", "sympy.explainer.build_text")
    for fn in ("grade", "grade_part", "grade_multi", "analyze_work", "grade_graph_check"):
        if hasattr(grader, fn):
            wrap(grader, fn, f"sympy.grader.{fn}")
    wrap(services, "score_work", "sympy.rubric.score_work")

    # ---- services glue ---------------------------------------------------
    wrap(services, "_steps_text", "svc._steps_text")
    wrap(services, "_build_explanation", "svc._build_explanation (cache→LLM→persist)")
    wrap(services, "km_solution_for_question", "svc.km_solution_for_question")
    wrap(services, "record_skill_progress", "svc.record_skill_progress")
    wrap(services, "_upsert_session", "svc._upsert_session")

    # ---- background usage-log writer: keep it out of the timeline ---------
    from engine import pricing

    orig_write = pricing._write_usage_log

    async def quiet_write(*a, **kw):
        SUPPRESS.set(True)  # this task has its own context copy
        return await orig_write(*a, **kw)

    pricing._write_usage_log = quiet_write

    # ---- database --------------------------------------------------------
    wrap(AsyncSession, "get", "db.get", note_fn=lambda s, m, *_, **__: getattr(m, "__name__", str(m)))
    wrap(AsyncSession, "execute", "db.execute", note_fn=lambda s, stmt, *_, **__: " ".join(str(stmt).split())[:70])
    wrap(AsyncSession, "scalar", "db.scalar", note_fn=lambda s, stmt, *_, **__: " ".join(str(stmt).split())[:70])
    wrap(AsyncSession, "scalars", "db.scalars", note_fn=lambda s, stmt, *_, **__: " ".join(str(stmt).split())[:70])
    wrap(AsyncSession, "flush", "db.flush")
    wrap(AsyncSession, "commit", "db.commit")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def category(sp: Span) -> str:
    n = sp.name
    if n == "gemini.api_call":
        return "LLM: Gemini API (network + generation)"
    if n.startswith("llm.ollama") or n == "ocr.ollama_call":
        return "LLM: Ollama"
    if n.startswith("ocr.preprocess"):
        return "Image preprocessing (PIL)"
    if n.startswith("sympy."):
        return "SymPy / deterministic engine"
    if n.startswith("db."):
        return "Postgres"
    if n.startswith("cache."):
        return "Redis"
    return "Python glue / other (incl. JSON parse, base64, logging)"


def render_work(lines):
    font = None
    for p in ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            font = ImageFont.truetype(p, 34)
            break
        except OSError:
            pass
    font = font or ImageFont.load_default()
    line_h = 64
    width = max(1100, int(max((font.getlength(t) for t in lines), default=0)) + 60)
    img = Image.new("RGB", (width, line_h * len(lines) + 60), "white")
    d = ImageDraw.Draw(img)
    for i, t in enumerate(lines):
        d.text((30, 30 + i * line_h), t, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def fence(text, lang=""):
    text = str(text)
    return f"```{lang}\n{text}\n```"


def jdump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


def short(obj, limit=300):
    if isinstance(obj, dict):
        return {k: short(v, limit) for k, v in obj.items()}
    if isinstance(obj, list):
        return [short(v, limit) for v in obj]
    if isinstance(obj, str) and len(obj) > limit:
        return obj[:limit] + f"... [{len(obj)} chars]"
    return obj


def timeline_table(spans: list[Span], t0: float) -> str:
    rows = ["| t+ ms | total ms | self ms | span | detail |", "|---:|---:|---:|---|---|"]
    for sp in spans:
        indent = "&nbsp;&nbsp;" * sp.depth
        note = (sp.note or "").replace("|", "\\|")
        if sp.extra.get("error"):
            note += f" **ERROR:** {sp.extra['error']}".replace("|", "\\|")
        rows.append(
            f"| {(sp.start - t0) * 1000:.0f} | {sp.ms:.0f} | {sp.self_ms:.0f} | {indent}{sp.name} | {note} |"
        )
    return "\n".join(rows)


def breakdown_table(spans: list[Span], total_ms: float) -> str:
    agg: dict[str, float] = {}
    for sp in spans:
        agg[category(sp)] = agg.get(category(sp), 0.0) + sp.self_ms
    rows = ["| where the time went (self time, no double counting) | ms | % |", "|---|---:|---:|"]
    for k, v in sorted(agg.items(), key=lambda kv: -kv[1]):
        rows.append(f"| {k} | {v:.0f} | {v / total_ms * 100:.1f}% |" if total_ms else f"| {k} | {v:.0f} | |")
    return "\n".join(rows)


def llm_details(spans: list[Span], vision_prompt: str) -> str:
    out = []
    api_by_parent = {id(s.parent): s for s in spans if s.name == "gemini.api_call"}
    n = 0
    for sp in spans:
        if not sp.name.startswith(("llm.gemini_text", "llm.gemini_vision", "llm.ollama_text", "ocr.ollama_call")):
            continue
        n += 1
        api = api_by_parent.get(id(sp))
        parent_desc = sp.parent.name if sp.parent else "?"
        out.append(f"#### LLM call {n}: `{sp.name}` (caller: `{parent_desc}`)")
        out.append("")
        out.append(f"- wrapper total: **{sp.ms:.0f} ms**"
                   + (f", of which Gemini API call: **{api.ms:.0f} ms**" if api else ""))
        if api and api.extra.get("usage"):
            u = api.extra["usage"]
            out.append(f"- tokens: prompt **{u['prompt_tokens']}**, output **{u['output_tokens']}**, "
                       f"thinking **{u['thinking_tokens']}**, total {u['total_tokens']}")
        if api:
            out.append(f"- model: `{api.note.split(' in=')[0]}`")
        if sp.extra.get("image_bytes"):
            out.append(f"- image sent: {sp.extra['image_bytes']:,} bytes")
        if sp.extra.get("error"):
            out.append(f"- **error:** `{sp.extra['error']}`")
        prompt = sp.extra.get("prompt")
        if prompt is not None:
            if prompt == vision_prompt:
                prompt = f"[OCR prompt from engine/vision.py PROMPT, {len(vision_prompt)} chars - elided]"
            out += ["", "Prompt:", fence(prompt)]
        resp = sp.extra.get("response", sp.extra.get("raw"))
        if resp is not None:
            out += ["", "Raw response:", fence(resp)]
        out.append("")
    if not n:
        out.append("_No LLM calls in this stage (served from cache / deterministic path)._")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Main run
# --------------------------------------------------------------------------- #
async def get_trace_user(db):
    from sqlalchemy import select

    from core import security
    from models import User

    email = "trace-pipeline@example.test"
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, hashed_password=security.hash_password("trace-pass-123"))
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def run_stage(label, coro_fn):
    """Run one top-level stage; return (span_slice, total_ms, result)."""
    start_idx = len(SPANS)
    t0 = time.perf_counter()
    sp, tok = _begin(label)
    try:
        result = await coro_fn()
    finally:
        _end(sp, tok)
    total = (time.perf_counter() - t0) * 1000
    return SPANS[start_idx:], t0, total, result


async def main(args):
    import base64

    import services
    from db import SessionLocal
    from engine import solver, vision
    from models import Question
    from schemas import GenerateRequest

    install_hooks()
    out_dir = Path(CONTAINER_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sections, summary = [], []

    async with SessionLocal() as db:
        user = await get_trace_user(db)

        for scenario in [s.strip() for s in args.scenarios.split(",") if s.strip()]:
            SPANS.clear()
            # 1. question ------------------------------------------------
            spans_q, tq0, ms_q, qd = await run_stage(
                "STAGE 0: generate question (not part of Check)",
                lambda: services.create_question(
                    db, GenerateRequest(topic=args.topic, difficulty=args.difficulty)),
            )
            question = await db.get(Question, qd["id"])
            solution = solver.solve(question.topic, question.question_type, question.spec)
            steps = solution["steps"]
            lines = [
                (s["detail"] or s["title"]).split("\n")[0].replace("\\(", "").replace("\\)", "").strip()
                for s in steps
            ][:4]
            lines = [l for l in lines if l]
            if scenario == "wrong":
                lines = lines[:2]  # later steps contain the true value; keep the work honest
            lines.append(f"= {'12345' if scenario == 'wrong' else solution['answer_exact']}")

            if args.image:
                png = Path(args.image).read_bytes()
            else:
                png = render_work(lines)
            img_name = f"pipeline-{stamp}-{scenario}.png"
            (out_dir / img_name).write_bytes(png)
            b64 = base64.b64encode(png).decode()

            # 2. OCR -------------------------------------------------------
            spans_o, to0, ms_o, det = await run_stage(
                "STAGE 1: OCR  (vision.detect_math)", lambda: vision.detect_math(png, user_id=user.id))

            det_lines = det.get("lines") or []
            answer = det.get("raw_text") or (det_lines[-1] if det_lines else "")
            work = "\n".join(det_lines) or None

            async def do_grade():
                return await services.grade_question(
                    db, user, question.id, answer, work, det.get("lines_boxes"), None, 0, None, None, lang=args.lang)

            # 3. grade -----------------------------------------------------
            spans_g, tg0, ms_g, res = await run_stage("STAGE 2: GRADE  (services.grade_question)", do_grade)

            # 4. explain: the client starts this in the background right after a wrong answer
            async def do_explain():
                return await services.explain_question(
                    db, user, question.id, answer, work, lang=args.lang, attempt_id=res["attempt_id"])

            expl = repeat = None
            if not res.get("correct"):
                expl = await run_stage("STAGE 3: EXPLAIN  (services.explain_question, background)", do_explain)
                if not args.no_repeat:
                    repeat = await run_stage("STAGE 3b: EXPLAIN AGAIN, same input (cache warm)", do_explain)

            student_wait = ms_o + ms_g
            summary.append((scenario, res.get("correct"), ms_o, ms_g, student_wait,
                            expl[2] if expl else None, repeat[2] if repeat else None))

            # ---- report section ------------------------------------------
            s = [f"## Scenario: {scenario}", ""]
            s += [f"Question `{question.id}` - {question.topic}/{question.question_type}, "
                  f"{question.difficulty}, lang={args.lang}", "",
                  f"> {question.prompt}", "",
                  f"Expected answer (SymPy): `{question.expected_answer}`", "",
                  f"**Student waits after pressing Check: OCR {ms_o:.0f} ms + grade {ms_g:.0f} ms "
                  f"= {student_wait:.0f} ms**"
                  + (f"  (explanation prepared in background: {expl[2]:.0f} ms; again with warm cache: {repeat[2]:.0f} ms)"
                     if expl and repeat else (f"  (explanation prepared in background: {expl[2]:.0f} ms)" if expl else "")), ""]

            s += ["### Input", "", f"![work]({img_name})", "", "Text rendered into the image:", fence("\n".join(lines)), ""]

            for title, (sp_list, t0, tot) in [
                ("Stage 1 - OCR", (spans_o, to0, ms_o)),
                ("Stage 2 - Grade (SymPy only) + persist", (spans_g, tg0, ms_g)),
            ] + ([("Stage 3 - Explain (background, LLM)", (expl[0], expl[1], expl[2]))] if expl else []) \
              + ([("Stage 3b - Explain again (Redis cache warm)", (repeat[0], repeat[1], repeat[2]))] if repeat else []):
                s += [f"### {title}: {tot:.0f} ms", "", "**Timeline** (indent = nested call; self = time not spent in child calls)", "",
                      timeline_table(sp_list, t0), "", breakdown_table(sp_list, tot), "",
                      "**LLM calls in this stage**", "", llm_details(sp_list, vision.PROMPT), ""]

            s += ["### Data: OCR result (what the backend returned to the browser)", "",
                  fence(jdump(short(det)), "json"), "",
                  "### Data: grade request (what the browser sent)", "",
                  fence(jdump({"question_id": str(question.id), "user_answer": answer, "work_text": work,
                               "lines_boxes": det.get("lines_boxes"), "lang": args.lang}), "json"), "",
                  "### Data: grade response (what the student sees)", ""]
            for key in ("explanation", "work_check", "teacher_feedback"):
                if isinstance(res.get(key), dict):
                    s += [f"**{key}** (provider `{res[key].get('provider')}`):", "", fence(res[key].get("content", "")), ""]
            s += ["Full JSON:", fence(jdump(short(res, 600)), "json"), ""]
            if expl:
                s += ["### Data: explain response (shown when the student clicks Explain)", ""]
                for key in ("content", "work_check", "teacher_feedback"):
                    val = expl[3].get(key)
                    if isinstance(val, dict):
                        s += [f"**{key}** (provider `{val.get('provider')}`):", "", fence(val.get("content", "")), ""]
                    elif val:
                        s += [f"**{key}** (provider `{expl[3].get('provider')}`):", "", fence(val), ""]
            sections.append("\n".join(s))

    head = [
        f"# Pipeline trace - {datetime.now():%Y-%m-%d %H:%M:%S}", "",
        f"- topic `{args.topic}`, difficulty `{args.difficulty}`, lang `{args.lang}`",
        f"- handwriting: {'real image ' + args.image if args.image else 'synthetic (solution text rendered with a font; OCR timing realistic, accuracy is not)'}",
        "- measured in-process: excludes browser export/upload/download/render", "",
        "## Summary (ms)", "",
        "| scenario | correct | OCR | grade | **student waits** | explain (background) | explain (cache warm) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for sc, ok, o, g, w, ex, rg in summary:
        head.append(f"| {sc} | {ok} | {o:.0f} | {g:.0f} | **{w:.0f}** | {f'{ex:.0f}' if ex is not None else '-'} | {f'{rg:.0f}' if rg is not None else '-'} |")
    head.append("")
    path = out_dir / f"pipeline-{stamp}.md"
    path.write_text("\n".join(head + sections), encoding="utf-8")
    print(f"WROTE {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="limit")
    ap.add_argument("--difficulty", default="medium")
    ap.add_argument("--lang", default="en", choices=["en", "km"])
    ap.add_argument("--scenarios", default="correct,wrong", help="comma list of: correct, wrong")
    ap.add_argument("--image")
    ap.add_argument("--no-repeat", action="store_true", help="skip the warm-cache second explain of wrong answers")
    ap.add_argument("--container", default=None)  # consumed by host mode
    asyncio.run(main(ap.parse_args()))
