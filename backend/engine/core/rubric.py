"""Deterministic, step-by-step points rubric — generalizes the marking
scheme built for the 2018 past exam (``engine/topics/past_exam/rubric.py``)
to every topic's live/generated questions, not just that one exam.

The past-exam rubric could hand-list each question's graded steps because
the numbers are fixed (a real, historical paper). A generated exercise's
numbers are different every time, so its rubric can't be hand-typed —
instead it's derived mechanically from the exact same ``checkpoints`` list
every topic's ``solve()`` already returns for the live step-by-step
overlay (``analyze_work``'s ``formula_breakdown``). Two rules, same as the
past-exam rubric:

  1. A multi-part question's points split across its parts proportional to
     how many graded steps each part's own derivation has.
  2. Within one part/checkpoint-list with more than one step, the LAST step
     (that part's own final answer) gets 40% of that part's points; the
     remaining steps split the other 60% evenly.

There is no "real total" for a generated question, so ``question_points``
defaults to 10 (documented default, override freely) rather than being
derived from anything.

Matching a scalar/vector checkpoint is intentionally ORDER-TOLERANT (search
any of the item's remaining, not-yet-claimed lines) — the existing
"any_order" convention this codebase already uses for probability/functions.
A structured final answer (a domain interval, an odd/even classification, a
monotonicity table, ...) is graded by reusing ``grade_part``/``grade``'s own
existing judge for that ``answer_kind`` (interval/choice/sign/monotonicity/
variation_table/continuity) rather than re-implementing it — those judges
already are the deterministic authority for those shapes.
"""
from fractions import Fraction

from sympy import Expr, oo, simplify, sympify

from .dispatch import solve
from .grading import _numeric_close, grade, grade_part, parse_answer

# Structured final-answer kinds with a legitimate single-line typed answer
# a student could actually write ("domain is (2, oo)", "continuous"), so
# `grade`/`grade_part`'s own judge for that kind is reused for the final
# step. Deliberately excludes "variation_table" (and, if it ever appears
# here, "draw"): those `want`s have no single correct line of text at all —
# the table/graph is meant for the frontend to render, and every fact it
# contains is already covered by that item's own intermediate checkpoints —
# so their synthetic final step is dropped as ungradable-by-text instead
# (same as an intermediate structured value with no judge of its own).
_STRUCTURED_KINDS = {"interval", "choice", "sign", "monotonicity", "continuity"}

DEFAULT_QUESTION_POINTS = 10


# ---------------------------------------------------------------------------
# Matching a scalar/vector checkpoint against one student line.
# ---------------------------------------------------------------------------

def _value_str(text):
    text = text.strip()
    return text.rpartition("=")[2].strip() if "=" in text else text


def _parse_vector_text(text):
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    elif text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    comps = [c.strip() for c in text.split(",") if c.strip()]
    if not comps:
        raise ValueError("empty vector")
    return [parse_answer(c) for c in comps]


def is_simple_value(value):
    """True when `value` is a plain SymPy scalar/oo, or a list/tuple of such
    (a vector/point) — the shapes `step_matches` can judge directly. False
    for a structured answer (domain-interval list of dicts, a monotonicity
    piece-list, a variation table, ...), which needs its own answer_kind
    judge instead (see ``_STRUCTURED_KINDS``)."""
    if isinstance(value, (int, float, Expr)) or value in (oo, -oo):
        return True
    if isinstance(value, (list, tuple)):
        return len(value) > 0 and all(isinstance(v, (int, float, Expr)) for v in value)
    return False


def step_matches(text, expected, tol=1e-4):
    """True when `text` (one student line) asserts the scalar/vector value
    `expected` (see `is_simple_value` — never called on a structured value)."""
    value_str = _value_str(text)
    if isinstance(expected, (list, tuple)):
        try:
            got = _parse_vector_text(value_str)
        except Exception:
            return False
        if len(got) != len(expected):
            return False
        return all(_scalar_matches(g, sympify(e), tol) for g, e in zip(got, expected))
    try:
        value = parse_answer(value_str)
    except Exception:
        return False
    return _scalar_matches(value, expected, tol)


def _scalar_matches(value, expected, tol):
    if expected in (oo, -oo):
        return value == expected
    try:
        if simplify(value - expected) == 0:
            return True
    except Exception:
        pass
    try:
        # A malformed/list-shaped student line can parse to something that
        # isn't a plain SymPy scalar (e.g. a Python list) — `_numeric_close`
        # only guards against TypeError/ValueError, not every shape
        # mismatch, so this call is wrapped broadly rather than crashing the
        # whole marking pass over one bad line.
        return _numeric_close(value, expected, tol)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Rubric construction: derive graded items + steps from solve()'s own
# checkpoints/parts, then apply the two weighting rules mechanically.
# ---------------------------------------------------------------------------

def _split_final_intermediate(points, n):
    if n <= 1:
        return [points]
    final = points * Fraction(2, 5)
    each = (points - final) / (n - 1)
    return [each] * (n - 1) + [final]


def _item_checkpoints(answer_exact, checkpoints):
    """A part/solution's own checkpoints, guaranteed to end with a step
    whose value is that item's `answer_exact` (mirrors `analyze_work`'s own
    fix-up: several topics' checkpoints stop one step short of the literal
    final subtraction/combination, e.g. a definite integral's checkpoints
    end at F(lower), not the antiderivative difference)."""
    cps = list(checkpoints or [])
    if not cps or cps[-1]["value"] != answer_exact:
        cps.append({"label": "final answer", "value": answer_exact, "formula": None})
    return cps


def build_rubric(topic, question_type, params, question_points=DEFAULT_QUESTION_POINTS):
    """[{"item", "label", "value"|"kind", "points", "answer_kind", ...}] for
    one live/generated question, mechanically weighted per the module
    docstring's two rules. Never hand-typed — every value/kind comes
    straight from this exercise's own ``solve()`` output."""
    solution = solve(topic, question_type, params)
    parts = solution.get("parts")
    if parts:
        items = [{"label": p["label"], "answer_kind": p.get("answer_kind"),
                  "answer_exact": p["answer_exact"],
                  "checkpoints": _item_checkpoints(p["answer_exact"], p.get("checkpoints"))}
                 for p in parts]
    else:
        items = [{"label": question_type, "answer_kind": solution.get("answer_kind"),
                  "answer_exact": solution["answer_exact"],
                  "checkpoints": _item_checkpoints(solution["answer_exact"], solution.get("checkpoints"))}]

    question_points = Fraction(question_points)
    # Item weight uses the FULL checkpoint count (even a step that turns out
    # ungradable below still reflects that item's derivation length), but
    # points are only ever split among the steps actually kept.
    weights = [len(it["checkpoints"]) for it in items]
    total_w = sum(weights) or 1
    rubric = []
    for it, w in zip(items, weights):
        cps = it["checkpoints"]
        kept = []
        for idx, cp in enumerate(cps):
            is_final = idx == len(cps) - 1
            if is_simple_value(cp["value"]):
                kept.append((cp, "simple", None))
            elif is_final and it["answer_kind"] in _STRUCTURED_KINDS:
                kept.append((cp, "judged", it["answer_kind"]))
            # else: a structured value with no independent judge for it
            # (e.g. an intermediate domain-interval listing before its own
            # boundary checkpoints) — ungradable via this simple line-by-line
            # method, so it's dropped rather than crashing or scoring it 0.
        if not kept:
            continue
        per_item = question_points * w / total_w
        pts = _split_final_intermediate(per_item, len(kept))
        for (cp, kind, answer_kind), p in zip(kept, pts):
            rubric.append({
                "item": it["label"], "label": cp["label"], "points": p,
                "kind": kind, "value": cp["value"], "answer_kind": answer_kind,
            })
    return rubric


# ---------------------------------------------------------------------------
# Scoring: match a student's full written work against the rubric.
# ---------------------------------------------------------------------------

def score_work(topic, question_type, params, lines, question_points=DEFAULT_QUESTION_POINTS, tolerance=None):
    """Deterministic step-by-step score for one exercise's full written
    work. `lines`: the student's raw work, one asserted fact per line, any
    order (see module docstring). A "simple" step is matched against any of
    the not-yet-claimed lines; a "judged" step (a structured final answer)
    is graded by trying `grade`/`grade_part` on each not-yet-claimed line in
    turn, so it still benefits from those judges' own tolerant parsing.

    A student who combines several checkpoints into one condensed line
    (writing `|z| = sqrt(144+25)` straight to the answer instead of separate
    `a^2 = 144` / `b^2 = 25` lines) still has every earlier checkpoint in
    that same item implied by whichever later one a line DID match — the
    later value couldn't have been reached without them. So after the literal
    per-step matching pass, any of an item's checkpoints that sit before its
    own last actually-matched checkpoint are credited too, even with no line
    of their own — mirrors `analyze_work`'s own forward-matching leniency
    (a line is allowed to satisfy a checkpoint further ahead than the next
    expected one) instead of contradicting it with a stricter, line-per-value
    rubric. A checkpoint AFTER the last real match earns nothing — it must
    still be independently demonstrated, not merely implied by a later one
    that was never written.

    Returns {"earned", "possible", "breakdown"} — earned/possible are exact
    Fractions; never an LLM judgment call."""
    rubric = build_rubric(topic, question_type, params, question_points)
    work = [ln.strip() for ln in lines if ln.strip()]
    used = [False] * len(work)
    matched_line_idx = [None] * len(rubric)
    for idx, step in enumerate(rubric):
        for i, raw in enumerate(work):
            if used[i]:
                continue
            if step["kind"] == "simple":
                ok = step_matches(raw, step["value"], tolerance or 1e-4)
            else:
                ok = _judged_step_matches(topic, question_type, params, step, raw, tolerance)
            if ok:
                matched_line_idx[idx] = i
                used[i] = True
                break

    item_step_indices = {}
    for idx, step in enumerate(rubric):
        item_step_indices.setdefault(step["item"], []).append(idx)
    implied = set()
    for idxs in item_step_indices.values():
        last_matched_pos = max(
            (pos for pos, idx in enumerate(idxs) if matched_line_idx[idx] is not None),
            default=None,
        )
        if last_matched_pos is not None:
            for pos in range(last_matched_pos):
                idx = idxs[pos]
                if matched_line_idx[idx] is None:
                    implied.add(idx)

    breakdown = []
    earned = Fraction(0)
    possible = Fraction(0)
    for idx, step in enumerate(rubric):
        possible += step["points"]
        matched = matched_line_idx[idx]
        credit = matched is not None or idx in implied
        if credit:
            earned += step["points"]
        entry = {
            "item": step["item"], "label": step["label"],
            "points_earned": step["points"] if credit else Fraction(0),
            "points_possible": step["points"],
            "matched_line": work[matched] if matched is not None else None,
        }
        if idx in implied:
            entry["implied"] = True
        breakdown.append(entry)
    return {"earned": earned, "possible": possible, "breakdown": breakdown}


def _judged_step_matches(topic, question_type, params, step, line, tolerance):
    try:
        if step["item"] != question_type:
            verdict = grade_part(topic, question_type, params, step["item"], line, tolerance)
        else:
            verdict = grade(topic, question_type, params, line, tolerance)
    except Exception:
        return False
    return bool(verdict.get("correct"))
