"""Function-study generation: curated real BAC II exercises (multi-part study
problems) loaded once at import from backend/data/functions/*.json — the same
curated-replay pattern as limits. The exercise card carries the full part list
and the MoEYS narration; SymPy recomputes every answer at solve time."""
import json
import os

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "functions")


def _load():
    pool = []
    try:
        files = sorted(f for f in os.listdir(_CATALOG_DIR) if f.endswith(".json"))
    except OSError:
        files = []
    for fname in files:
        try:
            with open(os.path.join(_CATALOG_DIR, fname), encoding="utf-8") as f:
                item = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(item, dict) and item.get("parts"):
            pool.append(item)
    return pool


_FUNCTION_CURATED_TEMPLATES = _load()


def _build_curated_function(item):
    params = {k: v for k, v in item.items() if k not in ("prompt", "prompt_latex")}
    params["source_id"] = item.get("id")
    display = f"function study ({item.get('id')})"
    return {
        "topic": "functions",
        "question_type": "study",
        "difficulty": item.get("difficulty", "hard"),
        "params": params,
        "z_display": display,
        "z_latex": display,
        "prompt": item.get("prompt") or "",
        "prompt_latex": item.get("prompt_latex"),
        "source": "curated",
    }


def _generate_functions(rng, difficulty, question_type=None):
    if question_type not in (None, "study"):
        raise ValueError(f"question_type {question_type} does not match topic functions")
    pool = [t for t in _FUNCTION_CURATED_TEMPLATES if t.get("difficulty") == difficulty]
    if not pool:
        pool = _FUNCTION_CURATED_TEMPLATES
    if not pool:
        raise ValueError(f"no curated function exercises for difficulty {difficulty}")
    return _build_curated_function(rng.choice(pool))