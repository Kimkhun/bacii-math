"""Unified async LLM access: Gemini (Vertex AI) primary, local Ollama fallback.

Every function here is best-effort: on error it returns `None` so callers can fall
back. The math itself is never produced by an LLM — SymPy remains the source of truth.
"""
import json
import os

import httpx
from google import genai
from google.genai import types
from google.oauth2 import service_account

from core.config import settings

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


async def _gemini_generate(prompt: str, json_mode: bool = False) -> str:
    config = types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
    resp = await _gemini_client().aio.models.generate_content(
        model=settings.gemini_model, contents=prompt, config=config
    )
    return resp.text


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


async def narrate(steps_text: str, allow_gemini: bool = True) -> tuple[str | None, str | None]:
    prompt = (
        "Explain the solution below in a concise, no-nonsense style.\n"
        "For each step write ONE short line: the key computation and its result. "
        "At most one sentence per step.\n"
        "No greeting, no closing, no headings, no analogies, no encouragement, "
        "no markdown. Just the math, step by step.\n"
        "Follow the given steps exactly; do not invent new math.\n\n"
        f"{steps_text}"
    )
    return await _generate_with_fallback(prompt, allow_gemini)


def _step_check_summary(step_check: dict | None) -> str:
    if not step_check or not step_check.get("line_results"):
        return ""
    lines = []
    for r in step_check["line_results"]:
        if not r.get("checked"):
            continue
        verdict = "OK, matches " + r["matches"] if r.get("correct") else "WRONG at this step"
        lines.append(f"  line {r['line']} (\"{r['text']}\"): {verdict}")
    if not lines:
        return ""
    first_error = step_check.get("first_error_line")
    header = (
        f"\nVERIFIED STEP CHECK (computed exactly by SymPy, not a guess — trust this over your "
        f"own judgment of the algebra):\n" + "\n".join(lines) + "\n"
    )
    if first_error:
        header += f"The first line that is mathematically wrong is line {first_error}. Center your answer on that line.\n"
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
        "Check the student's work against the correct solution, step by step:\n"
        "- If the student's work is fully correct, say so in one short line.\n"
        "- Otherwise, point out the FIRST mistake: which line of the student's work "
        "is wrong, why it is wrong, and what the correct value should be at that step. "
        "If a VERIFIED STEP CHECK is given above, that line number is authoritative — do not "
        "second-guess it or pick a different line.\n"
        "- Mention what the student got right, if anything.\n"
        "Be concise: max 6 lines. No greeting, no closing, no markdown."
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
