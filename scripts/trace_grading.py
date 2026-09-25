#!/usr/bin/env python3
"""Trace the full "Check my answer" pipeline and write it to a Markdown report.

Drives the RUNNING stack over HTTP exactly like the web app does:

  generate question -> POST /vision/detect (OCR) -> POST /problems/grade

and records every request/response with wall-clock timings. Afterwards it pulls
the per-LLM-call rows (prompt, raw response, tokens, latency) that the backend
wrote to `api_usage_logs` for the trace user, so the report shows both the
student-visible timeline and what happened inside each Gemini/Ollama call.

Usage:
  python scripts/trace_grading.py                        # limit topic, correct + wrong
  python scripts/trace_grading.py --topic integral --lang km
  python scripts/trace_grading.py --image my_work.png    # real handwriting photo
  python scripts/trace_grading.py --scenarios wrong --out /tmp/trace.md

Notes:
  * Signs up a throwaway user (trace-<timestamp>@example.test) unless
    --email/--password of an existing account are given. It creates real
    Question/Attempt rows in the DB; nothing is deleted afterwards.
  * Without --image, the "handwriting" is the solution steps rendered with a
    font: timings are representative, OCR accuracy on real ink is not.
  * LLM-call details need `docker exec bacii-postgres-1 psql`; they are skipped
    with a note if docker is unavailable.
"""
import argparse
import base64
import io
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_CANDIDATES = [
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def render_work(lines: list[str]) -> bytes:
    font = None
    for path in FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(path, 34)
            break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    line_h = 64
    width = max(1100, int(max((font.getlength(t) for t in lines), default=0)) + 60)
    img = Image.new("RGB", (width, line_h * len(lines) + 60), "white")
    d = ImageDraw.Draw(img)
    for i, text in enumerate(lines):
        d.text((30, 30 + i * line_h), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _short(obj, limit=400):
    """Copy of obj with long strings (base64 images etc.) elided, for display."""
    if isinstance(obj, dict):
        return {k: _short(v, limit) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_short(v, limit) for v in obj]
    if isinstance(obj, str) and len(obj) > limit:
        return obj[:limit] + f"... [{len(obj)} chars total]"
    return obj


class Tracer:
    def __init__(self, base: str):
        self.client = httpx.Client(base_url=base, timeout=180)
        self.token: str | None = None
        self.events: list[dict] = []

    def call(self, label: str, method: str, path: str, body=None, **kw):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        t0 = time.perf_counter()
        resp = self.client.request(method, path, json=body, headers=headers, **kw)
        ms = int((time.perf_counter() - t0) * 1000)
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        self.events.append({
            "label": label, "method": method, "path": path, "status": resp.status_code,
            "ms": ms, "request": body, "response": data,
        })
        return resp.status_code, data, ms


def fetch_llm_calls(email: str, since_iso: str) -> tuple[list[dict] | None, str]:
    sql = (
        "SELECT COALESCE(json_agg(t ORDER BY t.created_at), '[]'::json) FROM ("
        "SELECT l.created_at, l.endpoint, l.provider, l.model_name, l.prompt_tokens, "
        "l.completion_tokens, l.latency_ms, l.success, l.error_message, l.prompt_text, l.response_text "
        "FROM api_usage_logs l JOIN users u ON u.id = l.user_id "
        f"WHERE u.email = '{email}' AND l.created_at >= '{since_iso}') t"
    )
    try:
        out = subprocess.run(
            ["docker", "exec", "bacii-math-postgres-1", "psql", "-U", "postgres", "-d", "bacii", "-At", "-c", sql],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode != 0:
            return None, out.stderr.strip()
        return json.loads(out.stdout.strip() or "[]"), ""
    except Exception as exc:
        return None, str(exc)


def fence(text, lang=""):
    return f"```{lang}\n{text}\n```"


def jblock(obj):
    return fence(json.dumps(_short(obj), indent=2, ensure_ascii=False), "json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://localhost:8016")
    ap.add_argument("--topic", default="limit")
    ap.add_argument("--difficulty", default="medium")
    ap.add_argument("--lang", default="en", choices=["en", "km"])
    ap.add_argument("--scenarios", default="correct,wrong", help="comma list of: correct, wrong")
    ap.add_argument("--image", help="use this image as the handwriting instead of a rendered one")
    ap.add_argument("--email")
    ap.add_argument("--password")
    ap.add_argument("--out", help="report path (default: traces/trace-<timestamp>.md)")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = Path(args.out) if args.out else ROOT / "traces" / f"trace-{stamp}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tr = Tracer(args.base)
    email = args.email or f"trace-{stamp}@example.test"
    password = args.password or "trace-pass-123"
    since = datetime.now(timezone.utc).isoformat()

    if args.email:
        code, data, _ = tr.call("login", "POST", "/auth/login", {"email": email, "password": password})
    else:
        code, data, _ = tr.call("signup", "POST", "/auth/signup", {"email": email, "password": password})
    if code >= 400:
        sys.exit(f"auth failed ({code}): {data}")
    tr.token = data["access_token"]
    tr.events.clear()  # auth is not part of the pipeline being measured

    sections = []
    summary_rows = []
    for scenario in [s.strip() for s in args.scenarios.split(",") if s.strip()]:
        tr.events.clear()
        t_all = time.perf_counter()

        code, q, ms_gen = tr.call(
            "generate", "POST", "/problems/generate",
            {"topic": args.topic, "difficulty": args.difficulty},
        )
        if code >= 400:
            sections.append(f"## Scenario: {scenario}\n\nGenerate failed ({code}): {q}\n")
            continue
        code, detail, _ = tr.call("get question", "GET", f"/problems/{q['id']}")
        steps = detail.get("steps", []) if isinstance(detail, dict) else []
        work_lines = [
            (s.get("detail") or s.get("title") or "").split("\n")[0].replace("\\(", "").replace("\\)", "").strip()
            for s in steps
        ][:6]
        work_lines = [l for l in work_lines if l] or ["(no steps)"]
        if scenario == "wrong":
            work_lines[-1] = "= 12345"

        if args.image:
            png = Path(args.image).read_bytes()
        else:
            png = render_work(work_lines)
        img_name = f"trace-{stamp}-{scenario}.png"
        (out_path.parent / img_name).write_bytes(png)

        b64 = base64.b64encode(png).decode()
        code, det, ms_ocr = tr.call("OCR", "POST", "/vision/detect", {"image_base64": b64})
        if code >= 400:
            sections.append(f"## Scenario: {scenario}\n\nOCR failed ({code}): {det}\n")
            continue

        lines = det.get("lines") or []
        answer = det.get("raw_text") or (lines[-1] if lines else "")
        grade_body = {
            "question_id": q["id"], "user_answer": answer,
            "work_text": "\n".join(lines) or None, "lines_boxes": det.get("lines_boxes"),
            "hints_used": 0, "lang": args.lang,
        }
        code, res, ms_grade = tr.call("grade", "POST", "/problems/grade", grade_body)
        total_ms = int((time.perf_counter() - t_all) * 1000)
        student_wait = ms_ocr + ms_grade

        verdict = res.get("correct") if isinstance(res, dict) else f"HTTP {code}"
        summary_rows.append(
            f"| {scenario} | {verdict} | {ms_ocr} | {ms_grade} | **{student_wait}** |"
        )

        sec = [f"## Scenario: {scenario}", ""]
        sec.append(f"Question `{q['id']}` ({args.topic}/{q.get('question_type')}, {args.difficulty}, lang={args.lang})")
        sec.append("")
        sec.append(f"> {q.get('prompt')}")
        sec.append("")
        sec.append(f"**Student-visible wait after pressing Check = OCR {ms_ocr} ms + grade {ms_grade} ms = {student_wait} ms**")
        sec.append("")
        sec.append(f"### 1. Input image (`{img_name}`)")
        sec.append("")
        sec.append(f"![work]({img_name})")
        sec.append("")
        sec.append("Text used to render it (before OCR):")
        sec.append(fence("\n".join(work_lines)))
        sec.append("")
        sec.append(f"### 2. OCR — `POST /vision/detect` ({ms_ocr} ms)")
        sec.append("")
        sec.append("Response:")
        sec.append(jblock(det))
        sec.append("")
        sec.append(f"### 3. Grade request — `POST /problems/grade`")
        sec.append("")
        sec.append(jblock(grade_body))
        sec.append("")
        sec.append(f"### 4. Grade response ({ms_grade} ms)")
        sec.append("")
        if isinstance(res, dict):
            for key in ("correct", "reason", "given", "expected"):
                sec.append(f"- **{key}**: `{res.get(key)}`")
            sec.append("")
            for key in ("explanation", "work_check", "teacher_feedback"):
                if res.get(key):
                    sec.append(f"**{key}** (provider: `{res[key].get('provider')}`):")
                    sec.append("")
                    sec.append(fence(res[key].get("content", "")))
                    sec.append("")
            sec.append("Full response:")
        sec.append(jblock(res))
        sec.append("")
        sections.append("\n".join(sec))
        sections[-1] += f"\n_Scenario wall time incl. generate: {total_ms} ms (generate {ms_gen} ms)_\n"

    llm_calls, note = fetch_llm_calls(email, since)

    head = [
        f"# Grading pipeline trace — {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        f"- API: `{args.base}`  |  topic: `{args.topic}`  |  difficulty: `{args.difficulty}`  |  lang: `{args.lang}`",
        f"- Trace user: `{email}`",
        f"- Handwriting source: {'`' + args.image + '`' if args.image else 'synthetic (solution steps rendered with a font)'}",
        "",
        "## Summary (milliseconds)",
        "",
        "| scenario | correct | OCR | grade | student waits |",
        "|---|---|---|---|---|",
        *summary_rows,
        "",
    ]
    tail = ["## LLM calls made during the trace (from `api_usage_logs`)", ""]
    if llm_calls is None:
        tail.append(f"_Unavailable: {note}_")
    elif not llm_calls:
        tail.append("_No LLM calls were logged (all served from cache/deterministic paths, or logs not yet flushed)._")
    else:
        tail += ["| # | endpoint | provider/model | latency ms | in tok | out tok | ok |", "|---|---|---|---|---|---|---|"]
        for i, c in enumerate(llm_calls, 1):
            tail.append(
                f"| {i} | {c['endpoint']} | {c['provider']}/{c['model_name']} | {c['latency_ms']} | "
                f"{c['prompt_tokens']} | {c['completion_tokens']} | {c['success']} |"
            )
        tail.append("")
        for i, c in enumerate(llm_calls, 1):
            tail.append(f"### LLM call {i}: {c['endpoint']} ({c['latency_ms']} ms, {c['created_at']})")
            tail.append("")
            if c.get("error_message"):
                tail += [f"**Error:** `{c['error_message']}`", ""]
            tail += ["Prompt:", fence(c.get("prompt_text") or ""), "", "Raw response:", fence(c.get("response_text") or ""), ""]

    out_path.write_text("\n".join(head + sections + tail), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
