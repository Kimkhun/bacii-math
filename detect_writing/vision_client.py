"""Client for sending canvas snapshots to a local Ollama vision model
and getting back a transcription restricted to numbers/math symbols/functions.
"""
import base64
import json
import os

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.environ.get("VISION_MODEL", "qwen2.5vl:7b")

PROMPT = """You are looking at an image of digital handwriting/drawing on a canvas.
The writer is only writing numbers, math symbols, operators, or math functions
(e.g. digits 0-9, +, -, *, /, =, ^, sqrt, sin, cos, log, fractions, parentheses,
variables like x/y/a/b, etc). Ignore any stray marks or noise.

Transcribe exactly what is written as a math expression or equation.

Respond with ONLY a JSON object, no markdown fences, no extra text, in this exact shape:
{
  "raw_text": "<the equation as plain text, e.g. y = a*x + b>",
  "latex": "<the equation as LaTeX>",
  "tokens": ["<ordered list of individual symbols/numbers/operators/functions>"],
  "confidence": <float 0-1, your confidence this is a correct math transcription>
}

If the canvas is blank or nothing math-related is visible, respond with:
{"raw_text": "", "latex": "", "tokens": [], "confidence": 0.0}
"""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def recognize_math(image_path: str, timeout: float = 60.0) -> dict:
    """Send an image file to the local vision LLM and return a parsed dict."""
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "images": [image_b64],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0},
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    raw_response = data.get("response", "")

    cleaned = _strip_code_fence(raw_response)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = {
            "raw_text": raw_response.strip(),
            "latex": "",
            "tokens": [],
            "confidence": 0.0,
            "parse_error": True,
        }

    parsed.setdefault("raw_text", "")
    parsed.setdefault("latex", "")
    parsed.setdefault("tokens", [])
    parsed.setdefault("confidence", 0.0)
    return parsed
