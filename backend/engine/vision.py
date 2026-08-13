"""Server-side handwriting detection via a local Ollama vision model.

Receives a raw image, crops/upscales to the ink strokes, and asks the vision
model to transcribe the handwritten math answer.
"""
import base64
import io
import json

import httpx
from PIL import Image

from core.config import settings

PROMPT = """You are reading a single handwritten math ANSWER that a student wrote on a canvas.
The answer is short: a number, a fraction, or a small expression using digits 0-9 and
symbols + - * / = ^ sqrt pi ( ) and the letter i (imaginary unit).

Look closely at the ink strokes and transcribe the answer exactly as a math expression.

Respond with ONLY a JSON object, no markdown, no extra text, in this exact shape:
{"raw_text": "<the expression as plain text, e.g. 13 or -9+69 or pi/4 or 3-4i>",
 "latex": "<the same expression as LaTeX>",
 "tokens": ["<ordered individual symbols/numbers>"],
 "confidence": <float 0-1, your confidence>}

Only if the image is completely blank (no ink at all), respond with:
{"raw_text": "", "latex": "", "tokens": [], "confidence": 0.0}
"""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def _preprocess(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    bbox = gray.point(lambda p: 0 if p > 240 else 255).getbbox()
    if bbox is None:
        return image

    pad = 24
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(image.width, bbox[2] + pad)
    bottom = min(image.height, bbox[3] + pad)
    cropped = image.crop((left, top, right, bottom))

    w, h = cropped.size
    scale = max(1, min(1024 // max(w, 1), 1024 // max(h, 1), 4))
    if scale > 1:
        cropped = cropped.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
    return cropped


def preprocess_bytes(data: bytes) -> bytes:
    with Image.open(io.BytesIO(data)) as raw:
        image = _preprocess(raw.convert("RGB"))
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()


async def _ollama_generate(image_b64: str) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            settings.ollama_url,
            json={
                "model": settings.vision_model,
                "prompt": PROMPT,
                "images": [image_b64],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0},
            },
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()


async def detect_math(data: bytes) -> dict:
    processed = preprocess_bytes(data)
    image_b64 = base64.b64encode(processed).decode("utf-8")

    raw_response = await _ollama_generate(image_b64)
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
