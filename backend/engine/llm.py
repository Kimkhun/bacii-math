"""Unified async LLM access: Gemini (Vertex AI) primary, local Ollama fallback.

Every function here is best-effort: on error it returns `None` so callers can fall
back. The math itself is never produced by an LLM — SymPy remains the source of truth.
"""
import asyncio
import json
import os

import httpx
from google import genai
from google.genai import types
from google.oauth2 import service_account

from core.config import settings

from .formulas import resolve_formula

_client = None


def _credentials():
    path = settings.google_application_credentials
    if path and os.path.exists(path):
        return service_account.Credentials.from_service_account_file(
            path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
    return None


def _project():
    if settings.gemini_project:
        return settings.gemini_project
    path = settings.google_application_credentials
    if path and os.path.exists(path):
        with open(path) as f:
            return json.load(f)["project_id"]
    return None


def _gemini_client():
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=_project(),
            location=settings.gemini_location,
            credentials=_credentials(),
        )
    return _client


async def _gemini_generate(
    prompt: str,
    json_mode: bool = False,
    response_schema: dict | None = None,
    tools: list | None = None,
) -> any:
    if tools is not None:
        config = types.GenerateContentConfig(tools=tools, temperature=0.1)
    elif response_schema is not None:
        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=response_schema
        )
    else:
        config = types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
    resp = await asyncio.wait_for(
        _gemini_client().aio.models.generate_content(
            model=settings.gemini_model, contents=prompt, config=config
        ),
        timeout=settings.gemini_timeout_seconds,
    )
    if tools is not None:
        return resp
    return resp.text


async def gemini_vision_generate(prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str | None:
    """Best-effort Gemini vision call for handwriting OCR.

    Uses the same Vertex service account as the text/explanation calls, so the
    normal Gemini quota applies (Vertex API, not the consumer free tier).
    Returns None on any error so callers can fall back to Ollama.
    """
    model = settings.gemini_vision_model or settings.gemini_model
    try:
        resp = await asyncio.wait_for(
            _gemini_client().aio.models.generate_content(
                model=model,
                contents=[
                    types.Part(text=prompt),
                    types.Part(inline_data=types.Blob(mime_type=mime_type, data=image_bytes)),
                ],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            ),
            timeout=settings.gemini_timeout_seconds,
        )
        return resp.text
    except Exception:
        return None


async def _ollama_generate(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            settings.ollama_url,
            json={"model": settings.text_model, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()


async def _generate_with_fallback(prompt: str, allow_gemini: bool = True) -> tuple[str | None, str | None]:
    if allow_gemini:
        try:
            text = (await _gemini_generate(prompt)).strip()
            if text:
                return text, "gemini"
        except Exception:
            pass
    try:
        text = (await _ollama_generate(prompt)).strip()
        if text:
            return text, "ollama"
    except Exception:
        pass
    return None, None


async def narrate(steps_text: str, allow_gemini: bool = True, context: dict | None = None) -> tuple[str | None, str | None]:
    prompt = (
        "Explain the solution below in a concise, no-nonsense style.\n"
        "For each step write ONE short line: the key computation and its result. "
        "At most one sentence per step.\n"
        "No greeting, no closing, no headings, no analogies, no encouragement, "
        "no markdown. Just the math, step by step.\n"
        "Follow the given steps exactly; do not invent new math.\n"
        "Do not add any analysis not present in the given steps — no 'undefined', "
        "no domain restrictions, no alternative approaches.\n"
        "Write EVERY mathematical expression as LaTeX wrapped in \\( and \\) "
        "(e.g. \\( \\lim_{x\\to 2} \\frac{x^2-4}{x-2} = 4 \\)). Never write "
        "plain-text math like lim(x -> 2) or sqrt(x+1).\n\n"
        f"{steps_text}"
    )
    if context and context.get("user_answer"):
        part = context.get("part")
        expected = context.get("expected")
        expected_note = f" and the correct value for that part is '{expected}'" if expected else ""
        prompt = (
            f"CONTEXT: the student answered{subpart_label(part)} with "
            f"'{context['user_answer']}'{expected_note}.\n"
            "Briefly (one line, at the start) connect their answer to the correct one "
            "for that part, then explain the solution. Never invent math beyond the "
            "steps below.\n\n" + prompt
        )
    return await _generate_with_fallback(prompt, allow_gemini)


# Structured-output schema for the Khmer reference solution. Every mathematical
# value is locked: Gemini only fills the `khmer` prose fields, never the `latex`.
_KM_SOLUTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "parts": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "label": {"type": "STRING"},
                    "steps": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "khmer": {"type": "STRING"},
                                "latex": {"type": "STRING"},
                            },
                            "required": ["khmer", "latex"],
                        },
                    },
                    "answer_khmer": {"type": "STRING"},
                    "answer_latex": {"type": "STRING"},
                },
                "required": ["label", "steps", "answer_khmer", "answer_latex"],
            },
        }
    },
    "required": ["parts"],
}

_KM_PART_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "label": {"type": "STRING"},
        "steps": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "khmer": {"type": "STRING"},
                    "latex": {"type": "STRING"},
                },
                "required": ["khmer", "latex"],
            },
        },
        "answer_khmer": {"type": "STRING"},
        "answer_latex": {"type": "STRING"},
    },
    "required": ["label", "steps", "answer_khmer", "answer_latex"],
}

_KM_PART_TOOL_DECL = types.FunctionDeclaration(
    name="submit_part_solution",
    description="Submit an authentic Cambodian Bac II exam-style reference solution in Khmer for one part",
    parameters=_KM_PART_SCHEMA,
)


async def _narrate_single_part(part_fact: dict) -> dict | None:
    prompt = (
        "You are an expert Cambodian Bac II mathematics grader and teacher writing the official exam solution key (អត្រាកំណែផ្លូវការ).\n"
        f"Part Data (verified by SymPy):\n{json.dumps(part_fact, ensure_ascii=False)}\n\n"
        "RULES:\n"
        "- Write in the exact concise, elegant style of official Cambodian national exam keys (អត្រាកំណែផ្លូវការ). Do NOT write repetitive filler or wordy paragraphs.\n"
        "- Each step's `khmer` field MUST embed the mathematical `latex` equation directly inside $...$ (e.g. គេបាន $\\lim_{x\\to 3^-} g(x) = \\lim_{x\\to 3^-} \\ln\\left(\\frac{-x-3}{x-3}\\right) = \\ln\\left(\\frac{-6}{0^-}\\right) = +\\infty$). NEVER write empty phrases like `គេបាន៖` without including the math equation.\n"
        "- The explanation MUST be 100% in Khmer with NO English words.\n"
        "- Copy each mathematical `latex` expression EXACTLY without altering numbers, variables, or signs.\n"
        "- Write `answer_khmer` as a crisp conclusion line wrapping all math in $...$ (e.g. ដូចនេះ $\\lim_{x\\to 3^-} g(x) = +\\infty$ ឬ ដូចនេះ $a = 1, b = 1, c = 4$).\n"
        "- Use standard Cambodian Bac II connectors: គេមាន, គេបាន, នាំឱ្យ, លុះត្រាតែ, ដូចនេះ, ឯកតាផ្ទៃ.\n"
        "- If `want` is 'variation_table' or `answer_latex` is 'variation table', do NOT construct raw LaTeX matrix/array tables (\\begin{array}). The UI renders the authentic graphical variation table automatically. Write 1 concise step explaining the derivative sign and limits on the domain, and write `answer_khmer` as 'សម្រាប់តារាងអថេរភាព សូមមើលតារាងខាងលើ'.\n"
        "- You MUST call the `submit_part_solution` tool with the filled part solution."
    )
    try:
        tool = types.Tool(function_declarations=[_KM_PART_TOOL_DECL])
        resp = await _gemini_generate(prompt, tools=[tool])
        if hasattr(resp, "function_calls") and resp.function_calls:
            for call in resp.function_calls:
                if call.name == "submit_part_solution":
                    args = call.args
                    if isinstance(args, dict) and "steps" in args:
                        return args
        if hasattr(resp, "text") and resp.text:
            text = resp.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            if isinstance(data, dict) and "steps" in data:
                return data
        return None
    except Exception:
        return None


async def narrate_km_solution(facts: dict) -> dict | None:
    """Generate a school-style Khmer reference solution from SymPy-locked facts using Gemini tool calling.

    Processes sub-parts concurrently so even long 5-10 part function studies return quickly
    without hitting LLM token or timeout caps."""
    parts = facts.get("parts", [])
    if not parts:
        return None
    results = await asyncio.gather(*(_narrate_single_part(p) for p in parts))
    valid_parts = [r for r in results if r is not None]
    if not valid_parts:
        return None
    return {"parts": valid_parts}


def subpart_label(part):
    return f" part {part}" if part else ""


def _step_check_summary(step_check: dict | None) -> str:
    if not step_check or not step_check.get("line_results"):
        return ""
    lines = []
    for r in step_check["line_results"]:
        if not r.get("checked"):
            continue
        formula = r.get("formula")
        fname = f" ({resolve_formula(formula)['name_en']})" if formula else ""
        expected = r.get("expected")
        if r.get("correct"):
            verdict = f"OK, matches {r['matches']}{fname}"
            if expected:
                verdict += f" (expected value: {expected})"
        else:
            verdict = "could not verify against the expected step"
            if expected:
                verdict += f" (expected value: {expected})"
            verdict += fname
        lines.append(f"  line {r['line']} (\"{r['text']}\"): {verdict}")
    if not lines:
        return ""
    first_error = step_check.get("first_error_line")
    header = (
        f"\nSTEP CHECK (lines marked OK are verified exactly by SymPy; lines marked "
        f"'could not verify' are NOT certain):\n" + "\n".join(lines) + "\n"
    )
    if first_error:
        header += (
            f"The first line that could not be verified is line {first_error}. Re-check that "
            f"line yourself against the expected value above — it may be a real mistake or a "
            f"valid alternative step.\n"
        )
    return header


async def check_work(
    question_text: str,
    user_work: str,
    steps_text: str,
    answer: str,
    allow_gemini: bool = True,
    step_check: dict | None = None,
) -> tuple[str | None, str | None]:
    prompt = (
        "You are a math teacher checking a student's handwritten work line by line.\n\n"
        f"QUESTION: {question_text}\n\n"
        f"STUDENT'S WORK (transcribed from handwriting):\n{user_work}\n\n"
        f"CORRECT SOLUTION, ONE STEP PER LINE:\n{steps_text}\n\n"
        f"CORRECT ANSWER: {answer}\n"
        f"{_step_check_summary(step_check)}\n"
        "The question and the student's work may be in Khmer: work lines can mix Khmer "
        "words (e.g. ប្រូបាប៊ីលីតេ, ទាញបាន) with the math, and numbers may be written with "
        "Khmer digits (០-៩). Read the Khmer to understand what the student did, but judge "
        "only the MATH — the numbers and expressions. When quoting a value back, write it "
        "with Arabic digits.\n"
        "Check the student's work against the correct solution, step by step:\n"
        "- If the student's work is fully correct, say so in one short line.\n"
        "- Otherwise, point out the FIRST mistake: which line of the student's work "
        "is wrong, why it is wrong, and what the correct value should be at that step.\n"
        "- Lines marked OK in the STEP CHECK are certain — trust them. Lines marked "
        "'could not verify' are NOT certain: they may be a real mistake OR a valid "
        "alternative step. For those lines, compare the student's line against the "
        "expected value and the correct solution yourself; if the student used a "
        "valid alternative method, say the work is correct and move on.\n"
        "- If the student's work reaches the correct answer through valid steps, say "
        "it is correct. Do not flag correct work over pedantic caveats like domain "
        "restrictions on cancellation — only flag genuine algebra errors.\n"
        "- Mention what the student got right, if anything.\n"
        "Be concise: max 6 lines. No greeting, no closing, no markdown."
    )
    return await _generate_with_fallback(prompt, allow_gemini)


async def check_rubric_feedback(
    question_text: str,
    user_submission: str,
    correct_solution_km: str,
    is_correct: bool,
    allow_gemini: bool = True,
    step_check: dict | None = None,
) -> tuple[str | None, str | None]:
    """Generate authentic Khmer teacher commentary on the student's solution presentation
    and exam technique according to official Bac II grading rubrics."""
    status_str = "ត្រឹមត្រូវ (Correct)" if is_correct else "មិនទាន់ត្រឹមត្រូវ (Incorrect)"
    prompt = (
        "You are an expert Cambodian Bac II mathematics teacher and national exam grader reviewing a student's answer.\n"
        f"QUESTION: {question_text}\n\n"
        f"STUDENT'S SUBMISSION:\n{user_submission}\n\n"
        f"OFFICIAL EXAM KEY (អត្រាកំណែផ្លូវការ):\n{correct_solution_km}\n\n"
        f"SYMPY VERDICT: {status_str}\n"
        f"{_step_check_summary(step_check)}\n\n"
        "RULES:\n"
        "- Write your response 100% in authentic Khmer.\n"
        "- Give 2 to 3 concise, friendly, and constructive sentences offering actionable teacher feedback on their presentation according to the Bac II grading rubric (អត្រាកំណែ).\n"
        "- If their answer is correct, praise their accuracy and give a quick tip on presentation (e.g. remember to write domain conditions, mention question references like 'តាមសំណួរ...', or include units like ឯកតាផ្ទៃ).\n"
        "- If their answer is incorrect, pinpoint where they went off track and how to write it properly according to the official key.\n"
        "- Wrap all mathematical expressions in $...$.\n"
        "- Do NOT include English words. Keep it concise, helpful, and encouraging."
    )
    return await _generate_with_fallback(prompt, allow_gemini)


async def propose_problem(topic: str, difficulty: str) -> dict | None:
    prompt = (
        "You generate practice problems for a high-school math app. "
        f"Generate one {topic} problem at {difficulty} difficulty. "
        "The problem must be about a single complex number z = a + bi with integer "
        "coordinates a and b, with -20 <= a <= 20, -20 <= b <= 20, and b not zero. "
        "Respond with ONLY JSON, no markdown, in this exact shape:\n"
        '{"question_type": "<one of: modulus, argument, conjugate, real_part, imaginary_part>", '
        '"a": <int>, "b": <int>}'
    )
    try:
        text = await _gemini_generate(prompt, json_mode=True)
        data = json.loads(text)
        return {
            "question_type": str(data["question_type"]),
            "a": int(data["a"]),
            "b": int(data["b"]),
        }
    except Exception:
        return None
