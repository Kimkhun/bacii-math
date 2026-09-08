"""Past-exam generation: no randomization — each question_type replays one
verbatim historical exam question loaded once from ``data/curated/*.json``
at import (same parse-once-at-import pattern as every other topic's curated
pool)."""
import json
import os

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "data", "curated")


def _load():
    pool = {}
    try:
        files = sorted(f for f in os.listdir(_CATALOG_DIR) if f.endswith(".json"))
    except OSError:
        files = []
    for fname in files:
        try:
            with open(os.path.join(_CATALOG_DIR, fname), encoding="utf-8") as f:
                items = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(items, list):
            for item in items:
                pool[item["question_type"]] = item
    return pool


_PAST_EXAM_CATALOG = _load()


def _generate_past_exam(rng, difficulty, question_type=None):
    if question_type is None:
        pool = [qt for qt, item in _PAST_EXAM_CATALOG.items()
                if item.get("difficulty", "hard") == difficulty] or list(_PAST_EXAM_CATALOG)
        question_type = rng.choice(pool)
    item = _PAST_EXAM_CATALOG.get(question_type)
    if item is None:
        raise ValueError(f"unknown past_exam question_type: {question_type}")
    return {
        "topic": "past_exam",
        "question_type": question_type,
        "difficulty": item.get("difficulty", "hard"),
        "params": item["params"],
        "z_display": item.get("label", question_type),
        "z_latex": item.get("prompt_latex", ""),
        "prompt": item.get("prompt", ""),
        "prompt_latex": item.get("prompt_latex", ""),
        "source": "exam",
        "exam_id": item.get("exam_id"),
    }
