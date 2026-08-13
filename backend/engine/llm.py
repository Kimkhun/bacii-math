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


async def narrate(steps_text: str, allow_gemini: bool = True) -> tuple[str | None, str | None]:
    prompt = (
        "You are a patient high-school math tutor. Explain the solution below "
        "step by step in plain language, explaining the reasoning and any formulas "
        "used. Do not invent new math; follow the given steps exactly.\n\n"
        f"{steps_text}\n\nWrite a clear, friendly explanation."
    )
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
