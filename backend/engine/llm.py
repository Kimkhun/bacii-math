"""Unified LLM access: Gemini (Vertex AI) primary, local Ollama fallback.

Every function here is best-effort: on any error it returns `None` so callers can
fall back to the next provider or to deterministic output. The math itself is never
produced by an LLM — SymPy remains the source of truth.
"""
import json
import os

import requests
from google import genai
from google.genai import types
from google.oauth2 import service_account

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
TEXT_MODEL = os.environ.get("TEXT_MODEL", "qwen2.5:3b")

GEMINI_PROJECT = os.environ.get("GEMINI_PROJECT")
GEMINI_LOCATION = os.environ.get("GEMINI_LOCATION", "global")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
CREDENTIALS_PATH = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

_client = None


def _credentials():
    if CREDENTIALS_PATH and os.path.exists(CREDENTIALS_PATH):
        return service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
    return None


def _project():
    if GEMINI_PROJECT:
        return GEMINI_PROJECT
    if CREDENTIALS_PATH and os.path.exists(CREDENTIALS_PATH):
        with open(CREDENTIALS_PATH) as f:
            return json.load(f)["project_id"]
    return None


def _gemini_client():
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=_project(),
            location=GEMINI_LOCATION,
            credentials=_credentials(),
        )
    return _client


def _gemini_generate(prompt, json_mode=False):
    config = types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
    resp = _gemini_client().models.generate_content(
        model=GEMINI_MODEL, contents=prompt, config=config
    )
    return resp.text


def _ollama_generate(prompt):
    resp = requests.post(
        OLLAMA_URL,
        json={"model": TEXT_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def narrate(steps_text):
    prompt = (
        "You are a patient high-school math tutor. Explain the solution below "
        "step by step in plain language, explaining the reasoning and any formulas "
        "used. Do not invent new math; follow the given steps exactly.\n\n"
        f"{steps_text}\n\nWrite a clear, friendly explanation."
    )
    for backend in (_gemini_generate, _ollama_generate):
        try:
            text = backend(prompt).strip()
            if text:
                return text
        except Exception:
            continue
    return None


def propose_problem(topic, difficulty):
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
        text = _gemini_generate(prompt, json_mode=True)
        data = json.loads(text)
        return {
            "question_type": str(data["question_type"]),
            "a": int(data["a"]),
            "b": int(data["b"]),
        }
    except Exception:
        return None
