"""Server-side handwriting detection via a local Ollama vision model.

Receives a raw image, crops/upscales to the ink strokes, and asks the vision
model to transcribe the handwritten math answer.
"""
import base64
import io
import json
import re

import httpx
from PIL import Image

from core.config import settings
from engine import llm

PROMPT = r"""You are reading a student's HANDWRITTEN MATH WORK on a canvas. There may be just
one line (the final answer alone) or several lines (scratch work leading up to a final answer),
using digits 0-9 and symbols + - * / = ^ sqrt pi ( ) and the letter i (imaginary unit).

The student may be answering a Khmer word problem, so lines can mix Khmer text (words such as
ប្រូបាប៊ីលីតេ, ប៊ូល, ក្រហម) and/or Khmer digits (០១២៣៤៥៦៧៨៩) with the math. Transcribe
Khmer text and Khmer digits EXACTLY as written — do NOT convert them to Arabic digits and do NOT
drop them. The math symbols still go in plain text form (see below).

Step 1: read EVERY line of ink, top to bottom, exactly as written, into "lines" (one string
per line, in the order they appear on the page). Do not merge separate lines and do NOT skip
any line — include intermediate lines, the limit/integral notation, and the final answer line.

For each line, ALSO give "lines_latex": the same line typeset as LaTeX for display (e.g.
\frac{a}{b}, \lim_{x \to 4}, superscripts). lines_latex[i] must correspond one-to-one to
lines[i]. If a line contains Khmer words, put only the MATHEMATICAL parts as LaTeX and leave
the Khmer words out of lines_latex (it is display-only math; never force Khmer text into LaTeX).

For each line, ALSO give "lines_boxes": the bounding box of that line's ink, as four
normalized coordinates [x1, y1, x2, y2] each between 0 and 1, relative to the image
(left=0, right=1, top=0, bottom=1). The box must tightly enclose the line's actual ink
strokes (not empty space above/below). lines_boxes[i] must correspond one-to-one to lines[i].

IMPORTANT — "lines" MUST be plain-text math, NEVER LaTeX. Do NOT use \frac, \textstyle,
\displaystyle, \left, \right, \sqrt{}, or any backslash commands in "lines". Khmer glyphs are
allowed in "lines" (they are plain text, not LaTeX). Fractions go as
(a)/(b) with parentheses around the numerator AND denominator. Square roots go as sqrt(...).
Write limits in full including the arrow: "lim_{x -> 4} (x^2-16)/(x-4)". Examples:
  "lim_{x -> 4} (x^2-16)/(x-4)"
  "= ((x-4)(x+4))/(x-4)"
  "= x+4"
  "= 8"

Step 2: identify the FINAL ANSWER — usually the last line, or the value after "=" on the last
line — and report it again on its own as a clean math expression in "raw_text"/"latex"/
"tokens", the same way you would if it were the only thing written. If the answer was written
with Khmer digits, keep them in "raw_text" exactly as written. If the student wrote a sub-part
letter with their answer (A:, B:, C:, D:, P(A), P(B), or the Khmer letters ក. ខ. គ. ឃ.), keep it
in "raw_text" too, e.g. "B: 3/49" or "ខ: 3/49", so the app knows which part they answered.

Respond with ONLY a JSON object, no markdown, no extra text, in this exact shape:
{"lines": ["<line 1 plain ASCII>", "<line 2 plain ASCII>", ...],
 "lines_latex": ["<line 1 as LaTeX>", "<line 2 as LaTeX>", ...],
 "lines_boxes": [[x1, y1, x2, y2], [x1, y1, x2, y2], ...],
 "raw_text": "<final answer only, as plain text, e.g. 13 or -9+69 or pi/4 or 3-4i>",
 "latex": "<final answer only, as LaTeX>",
 "tokens": ["<ordered individual symbols/numbers of the final answer>"],
 "confidence": <float 0-1, your confidence in the final answer>}

Example — the canvas shows "lim (x^2-16)/(x-4)" then "= ((x-4)(x+4))/(x-4)" then "= x+4" then "= 8":
{"lines": ["lim_{x -> 4} (x^2-16)/(x-4)", "= ((x-4)(x+4))/(x-4)", "= x+4", "= 8"],
 "lines_latex": ["\lim_{x \to 4} \frac{x^2-16}{x-4}", "= \frac{(x-4)(x+4)}{x-4}", "= x+4", "= 8"],
 "lines_boxes": [[0.1, 0.05, 0.95, 0.2], [0.1, 0.25, 0.9, 0.4], [0.1, 0.45, 0.6, 0.6], [0.1, 0.65, 0.5, 0.8]],
 "raw_text": "8", "latex": "8", "tokens": ["8"], "confidence": 0.9}

Only if the image is completely blank (no ink at all), respond with:
{"lines": [], "lines_latex": [], "lines_boxes": [], "raw_text": "", "latex": "", "tokens": [], "confidence": 0.0}
"""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def _extract_braced(s: str, start: int) -> tuple[str, int]:
    """s[start] must be '{'. Returns (inner_text, index_after_closing_brace)."""
    depth = 0
    i = start
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1 : i], i + 1
        i += 1
    return s[start + 1 :], len(s)


def normalize_line(line: str) -> str:
    """Convert leaked LaTeX into plain ASCII math so downstream parsing works."""
    text = line
    text = (
        text.replace("\\textstyle", "")
        .replace("\\displaystyle", "")
        .replace("\\left", "")
        .replace("\\right", "")
        .replace("\\,", "")
        .replace("\\;", "")
        .replace("\\:", "")
        .replace("\\cdot", "*")
        .replace("\\times", "*")
        .replace("\\to", "->")
    )
    while "\\frac" in text:
        idx = text.index("\\frac")
        g1 = text.find("{", idx + 5)
        if g1 == -1:
            break
        num, g1_end = _extract_braced(text, g1)
        g2 = text.find("{", g1_end)
        if g2 == -1:
            break
        den, g2_end = _extract_braced(text, g2)
        text = text[:idx] + f"({normalize_line(num)})/({normalize_line(den)})" + text[g2_end:]
    text = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"sqrt(\1)", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_lines(lines) -> list[str]:
    return [normalize_line(line) for line in lines]


def _preprocess(image: Image.Image) -> tuple[Image.Image, dict | None]:
    """Crop to the ink strokes, pad, and upscale for the OCR model.

    Returns (processed_image, crop) where crop holds the original-image bounds
    (left/top/right/bottom) used to map the model's normalized line boxes back
    into the original image's pixel coordinates. crop is None when blank.
    """
    gray = image.convert("L")
    bbox = gray.point(lambda p: 0 if p > 240 else 255).getbbox()
    if bbox is None:
        return image, None

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
    return cropped, {"left": left, "top": top, "right": right, "bottom": bottom}


def _map_boxes_to_original(boxes, crop: dict | None) -> list | None:
    """Map the model's normalized line boxes (0-1 in the processed image) back to
    the original image's pixel coordinates. Returns a list parallel to `boxes`
    (None per entry when the box is missing/malformed), or None when there is no
    crop. The upscale factor cancels out, so only the crop offset/bounds matter."""
    if not crop:
        return None
    left, top = crop["left"], crop["top"]
    cw = crop["right"] - crop["left"]
    ch = crop["bottom"] - crop["top"]
    if cw <= 0 or ch <= 0:
        return None
    mapped = []
    for b in boxes:
        try:
            x1, y1, x2, y2 = (float(v) for v in b)
        except (TypeError, ValueError):
            mapped.append(None)
            continue
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            mapped.append(None)
            continue
        # Reject boxes that are implausibly tiny (junk output) — a real line of
        # handwriting is always at least a few pixels tall/wide in the crop.
        if (x2 - x1) * cw < 4 or (y2 - y1) * ch < 4:
            mapped.append(None)
            continue
        mapped.append([
            max(left, min(left + x1 * cw, crop["right"])),
            max(top, min(top + y1 * ch, crop["bottom"])),
            max(left, min(left + x2 * cw, crop["right"])),
            max(top, min(top + y2 * ch, crop["bottom"])),
        ])
    return mapped


def preprocess_bytes(data: bytes) -> bytes:
    with Image.open(io.BytesIO(data)) as raw:
        image, _ = _preprocess(raw.convert("RGB"))
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


async def _gemini_generate(image_b64: str) -> str | None:
    image_bytes = base64.b64decode(image_b64)
    return await llm.gemini_vision_generate(PROMPT, image_bytes)


def _finalize(parsed: dict, provider: str, crop: dict | None = None) -> dict:
    parsed.setdefault("lines", [])
    parsed.setdefault("lines_latex", [])
    parsed.setdefault("lines_boxes", [])
    parsed.setdefault("raw_text", "")
    parsed.setdefault("latex", "")
    parsed.setdefault("tokens", [])
    parsed.setdefault("confidence", 0.0)
    # Plain lines feed analyze_work / the LLM, so normalize any leaked LaTeX.
    # lines_latex is display-only and kept as LaTeX.
    parsed["lines"] = normalize_lines(parsed.get("lines", []))
    boxes = parsed.get("lines_boxes") or []
    # Boxes must line up one-to-one with lines or the overlay misaligns — drop all
    # of them when they don't (the UI falls back to the panel-only view).
    if len(boxes) == len(parsed["lines"]):
        mapped = _map_boxes_to_original(boxes, crop)
        parsed["lines_boxes"] = mapped or [None] * len(parsed["lines"])
    else:
        parsed["lines_boxes"] = [None] * len(parsed["lines"])
    parsed["provider"] = provider
    return parsed


async def detect_math(data: bytes) -> dict:
    with Image.open(io.BytesIO(data)) as raw:
        processed, crop = _preprocess(raw.convert("RGB"))
        buf = io.BytesIO()
        processed.save(buf, format="PNG")
        image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    raw_response: str | None = None
    provider = "ollama"

    if settings.vision_provider == "gemini":
        raw_response = await _gemini_generate(image_b64)
        provider = "gemini"
    elif settings.vision_provider == "fallback":
        try:
            raw_response = await _ollama_generate(image_b64)
            provider = "ollama"
        except Exception:
            raw_response = await _gemini_generate(image_b64)
            provider = "gemini"
    else:
        raw_response = await _ollama_generate(image_b64)

    if not raw_response:
        return _finalize(
            {"raw_text": "", "latex": "", "tokens": [], "confidence": 0.0, "parse_error": True},
            provider,
            crop,
        )

    cleaned = _strip_code_fence(raw_response)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = {
            "raw_text": cleaned.strip(),
            "latex": "",
            "tokens": [],
            "confidence": 0.0,
            "parse_error": True,
        }

    return _finalize(parsed, provider, crop)
