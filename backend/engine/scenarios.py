"""Scenario catalog for Khmer word-problem generation.

User-owned content, same pattern as `formulas.py`: JSON files in
`backend/data/scenarios/*.json` are loaded over nothing at import (there is no
built-in fallback — the catalog IS the content, and generation simply refuses to
run without it). Each entry is one parameterized sentence frame family:

    {
      "structure": "hypergeometric",   # solver structure (source of truth: solver.py)
      "difficulty": "medium",          # which difficulty pool the frame belongs to
      "want": "exactly_split",         # optional: the specific event asked about
      "slots": {                       # math parameters, sampled by the generator
        "w": {"min": 4, "max": 7},     #   integer range, or
        "p": {"values": ["1/2", "1/3"]}  #   explicit value list (fractions allowed)
      },
      "derived": {"n": "w + b"},       # slots computed from other slots (evaluated in order)
      "constraints": ["a <= w", "k - a <= b"],  # must all hold; sampled with retries
      "scenarios_km": ["...{w}..."],   # Khmer sentence frames (user-owned)
      "scenarios_en": ["...{w}..."]    # English reference frames (fallback display)
    }

The generator samples slots → evaluates `derived`/`constraints` → fills a frame.
The solver is the only authority on the math: every structure/want maps to a
solver branch, and the sampler only guarantees the params are *possible*
(constraints), never that they are correct (SymPy decides that).
"""
import ast
import json
import os
from fractions import Fraction

_CATALOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "scenarios")

_MAX_ATTEMPTS = 80


def _eval_expr(expr, env):
    """Evaluate a constraint/derived expression over Fraction-valued slots.

    Whitelisted AST only: ints, slot names, + - * // % **, comparisons,
    boolean and/or/not, unary minus. No calls, no attributes, no lists — the
    catalog is user-editable content, so arbitrary evaluation must be
    impossible by construction."""
    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, bool)):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in env:
                raise ValueError(f"unknown slot '{node.id}' in '{expr}'")
            return env[node.id]
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.Mod):
                return left % right
            if isinstance(node.op, ast.Pow):
                return left ** right
            raise ValueError(f"unsupported operator in '{expr}'")
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -walk(node.operand)
            if isinstance(node.op, ast.Not):
                return not walk(node.operand)
            raise ValueError(f"unsupported operator in '{expr}'")
        if isinstance(node, ast.Compare):
            ops = {
                ast.Lt: lambda a, b: a < b,
                ast.LtE: lambda a, b: a <= b,
                ast.Gt: lambda a, b: a > b,
                ast.GtE: lambda a, b: a >= b,
                ast.Eq: lambda a, b: a == b,
                ast.NotEq: lambda a, b: a != b,
            }
            left = walk(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                if not ops[type(op)](left, walk(comparator)):
                    return False
                left = walk(comparator)
            return True
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(walk(v) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(walk(v) for v in node.values)
            raise ValueError(f"unsupported operator in '{expr}'")
        raise ValueError(f"unsupported expression in '{expr}'")

    return walk(ast.parse(expr, mode="eval"))


def _to_fraction(value):
    return value if isinstance(value, Fraction) else Fraction(value)


def _sample_slot(spec, rng):
    if isinstance(spec, dict) and "values" in spec:
        return rng.choice(spec["values"])
    lo = spec.get("min", 1)
    hi = spec.get("max", 9)
    return rng.randint(lo, hi)


def _normalize(value):
    """Store ints as ints and fraction strings as strings ('1/2'), matching the
    solver's expectations (it sympifies fraction strings itself)."""
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return int(value.numerator)
        return f"{value.numerator}/{value.denominator}"
    return value


def fill_frame(frame, values):
    """Replace every {slot} in a sentence frame; any leftover brace is a bug in
    the catalog (slot not sampled) and must fail loudly."""
    for slot, value in values.items():
        frame = frame.replace("{" + slot + "}", str(value))
    if "{" in frame or "}" in frame:
        raise ValueError(f"unfilled slot left in frame: {frame!r}")
    return frame


def sample_scenario(entry, rng):
    """Sample valid params for a catalog entry, with retries.

    Multi-part entries (with "parts") return a list of {label, want, env} — one
    per sub-part, each carrying the shared sampled slots, that part's own
    overrides (e.g. its `a`), and the derived slots resolved for that part's
    merged env. Single-part entries return a one-element list. Returns None if
    no sampling satisfies every part's constraints."""
    parts = entry.get("parts")
    part_list = parts if parts else [{}]
    for _ in range(_MAX_ATTEMPTS):
        base = {name: _sample_slot(spec, rng) for name, spec in (entry.get("slots") or {}).items()}
        envs = []
        ok = True
        for part in part_list:
            overrides = {k: v for k, v in part.items() if k not in ("label", "want", "km", "en")}
            env = _resolve_env(entry, base, overrides)
            if env is None or not _constraints_ok(entry, env):
                ok = False
                break
            envs.append({
                "label": part.get("label"),
                "want": part.get("want") or entry.get("want"),
                "env": env,
            })
        if ok:
            return envs
    return None


def _resolve_env(entry, base, overrides=None):
    """base sampled slots + part overrides + derived slots (evaluated in order
    over the merged env), all normalized. None if any derived slot hard-fails.

    A derived slot whose expression references a slot this part doesn't define
    (e.g. kb = k - a on a part with no `a`) is skipped — the part's frames
    simply must not use it. Genuine errors (division by zero, unsupported
    operators) fail the whole env."""
    env = {name: _to_fraction(value) for name, value in base.items()}
    for name, value in (overrides or {}).items():
        try:
            env[name] = _to_fraction(value)
        except (ValueError, TypeError):
            env[name] = value  # non-numeric hint (wanted, want_label, other_label)
    for name, expr in (entry.get("derived") or {}).items():
        try:
            env[name] = _to_fraction(_eval_expr(expr, env))
        except ValueError:
            continue  # references a slot this part doesn't have
        except (TypeError, ZeroDivisionError):
            return None
    return {name: _normalize(value) for name, value in env.items()}


def _constraints_ok(entry, env):
    for expr in entry.get("constraints") or []:
        try:
            if not _eval_expr(expr, env):
                return False
        except (ValueError, TypeError, ZeroDivisionError):
            return False
    return True


def load_catalog():
    """Load backend/data/scenarios/*.json. Returns (scenarios, meta) where
    scenarios is {id: entry} and meta is {filename: meta-dict}. Malformed files
    and entries are skipped (same tolerance as the formulas loader)."""
    scenarios = {}
    meta = {}
    try:
        files = sorted(f for f in os.listdir(_CATALOG_DIR) if f.endswith(".json"))
    except OSError:
        return scenarios, meta
    for fname in files:
        try:
            with open(os.path.join(_CATALOG_DIR, fname), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("_meta"), dict):
            meta[fname] = data["_meta"]
        for sid, entry in data.items():
            if sid == "_meta" or not isinstance(sid, str) or not isinstance(entry, dict):
                continue
            if not entry.get("structure") or not entry.get("difficulty"):
                continue
            scenarios[sid] = entry
    return scenarios, meta


SCENARIOS, CATALOG_META = load_catalog()


def variant_by_difficulty(scenarios=None):
    """{difficulty: [scenario ids]} — drives the admin inventory rows and the
    generator's per-difficulty pools."""
    pools = {"easy": [], "medium": [], "hard": []}
    for sid, entry in (scenarios or SCENARIOS).items():
        pools.setdefault(entry.get("difficulty"), []).append(sid)
    return pools


VARIANT_BY_DIFFICULTY = variant_by_difficulty()


def by_id(sid):
    return SCENARIOS.get(sid)