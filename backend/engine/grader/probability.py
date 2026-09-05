"""Probability's multi-part grading: labeled/positional answer parsing
(``parse_multi_answers``), per-part verdicts (``grade_multi``), and grouping a
written work by part (``split_work_by_part`` / ``last_value_of_lines``)."""
import re as _re

from sympy import Symbol

from ..solver import solve
from .grader import (
    _DEFAULT_TOL,
    _equivalent_exact,
    _judge_by_kind,
    _numeric_close,
    parse_answer,
)


# ---------------------------------------------------------------------------
# Multi-part probability grading
#
# A probability exercise lists several sub-parts (A/B/C/D or ក/ខ/គ/ឃ) sharing
# one setup. The student submits an answer per part; every part's final answer
# is graded (exact or numeric) against its own SymPy-computed value. Formula
# and calculation checking happens separately via `analyze_work` on the merged
# checkpoints (each checkpoint is labeled with its part).
# ---------------------------------------------------------------------------

_PART_LABEL_PREFIX = _re.compile(r"^([^:=\s]+)\s*[:=]\s*(.+)$")

def _split_answer_tokens(text):
    """Split a multi-answer string on newlines/semicolons and on commas at
    paren depth 0 (so 'C(12,5), B: 3/11' splits correctly)."""
    tokens = []
    for chunk in _re.split(r"[;\n]", text):
        buf = []
        depth = 0
        for ch in chunk:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                tokens.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
        tokens.append("".join(buf))
    return [t.strip() for t in tokens if t.strip()]

def parse_multi_answers(text, labels):
    """Parse a multi-part answer submission into {label: value_str}.

    Accepts labeled values ('A: 14/99', 'B = 14/33', 'ខ: 2/3'), separated by
    commas/newlines/semicolons, and/or bare values assigned to the parts in
    order ('14/99, 14/33, 7/99, 92/99'). Labels are canonicalized against the
    given part labels (case-insensitive for Latin)."""
    text = (text or "").strip()
    if not text:
        return {}
    canonical = [str(l) for l in labels]

    def canon(key):
        for c in canonical:
            if c.upper() == key.upper():
                return c
        return None

    result = {}
    bare = []
    for tok in _split_answer_tokens(text):
        m = _PART_LABEL_PREFIX.match(tok)
        c = canon(m.group(1)) if m else None
        if c is not None:
            result[c] = m.group(2).strip()
        else:
            bare.append(tok)
    for value in bare:
        for c in canonical:
            if c not in result:
                result[c] = value
                break
    return result

def _judge_value(expected, user_answer, tol=_DEFAULT_TOL, kind=None, choices=None, exact_only=False, checkpoints=None):
    """Judge one answer value against an expected expression (probability), or
    dispatch to the right answer-shape judge for study-style topics (functions):
    interval / choice / infinity / line / expression / study-tables."""
    if kind:
        return _judge_by_kind(kind, expected, user_answer, tol, choices=choices, exact_only=exact_only, checkpoints=checkpoints)
    user = parse_answer(user_answer)
    x = Symbol("x")
    if _equivalent_exact(user, expected, x):
        return True, "exact", None
    if _numeric_close(user, expected, tol):
        return True, "numeric", None
    return False, "mismatch", None

def grade_multi(topic, question_type, params, submissions):
    """Grade every sub-part of a multi-part question.

    `submissions`: {label: value_str}. Each part's final answer is graded
    exactly/numerically against that part's SymPy answer. Overall `correct`
    requires every part to be answered AND correct. The response carries the
    per-part verdicts (`parts`) so the UI can show ✓/✗ per sub-question."""
    solution = solve(topic, question_type, params)
    parts = solution.get("parts") or []
    if not parts:
        raise ValueError("grade_multi requires a multi-part solution")
    verdicts = []
    for part in parts:
        label = part["label"]
        value = submissions.get(label)
        display = part.get("answer_display") or str(part["answer_exact"])
        if not value:
            verdicts.append({
                "label": label, "correct": False, "reason": "unanswered",
                "given": None, "expected": display,
                "answer_decimal": part["answer_decimal"],
            })
            continue
        try:
            correct, reason, note = _judge_value(
                part["answer_exact"], value, kind=part.get("answer_kind"),
                choices=part.get("choices"), exact_only=part.get("exact_only"),
                checkpoints=part.get("checkpoints"),
            )
        except Exception as exc:
            verdicts.append({
                "label": label, "correct": False,
                "reason": f"could not parse answer: {exc}",
                "given": value, "expected": display,
                "answer_decimal": part["answer_decimal"],
            })
            continue
        try:
            given = str(parse_answer(value))
        except Exception:
            given = value.strip()
        verdict = {
            "label": label, "correct": correct, "reason": reason,
            "given": given, "expected": display,
            "answer_decimal": part["answer_decimal"],
        }
        if note:
            verdict["note"] = note
        verdicts.append(verdict)

    n_correct = sum(1 for v in verdicts if v["correct"])
    n_total = len(verdicts)
    correct = n_correct == n_total
    reason = "all correct" if correct else f"{n_correct}/{n_total} correct"
    return {
        "correct": correct,
        "reason": reason,
        "parts": verdicts,
        "given": "; ".join(f"{v['label']}: {v['given'] or '—'}" for v in verdicts),
        "expected": str(solution["answer_exact"]),
        "answer_decimal": solution["answer_decimal"],
        "steps": solution["steps"],
        "graph": solution.get("graph"),
        "target_label": solution.get("target_label"),
    }

def split_work_by_part(lines, labels):
    """Group a student's written work lines by part label.

    A line belongs to the most recent part label seen ('A:', 'B:', 'ក.', or
    'P(A)'-style markers); leading unlabeled lines go to the first part and
    trailing ones to the last."""
    segments = {l: [] for l in labels}
    current = labels[0]
    for raw in lines:
        text = raw.strip()
        if not text:
            continue
        for l in labels:
            if _re.match(rf"^\s*{_re.escape(l)}\s*[:=.]\s*", text) or \
               _re.search(rf"P\s*\(\s*{_re.escape(l)}\s*\)", text):
                current = l
                break
        segments[current].append(text)
    return segments

def last_value_of_lines(lines):
    """The claimed final value of a part: the value on its last line (after any
    label prefix and '='), or None if no line carries a value."""
    for raw in reversed(lines):
        text = raw.strip()
        m = _PART_LABEL_PREFIX.match(text)
        if m:
            text = m.group(2).strip()
        if "=" in text:
            text = text.rpartition("=")[2].strip()
        text = _re.sub(r"^P\s*\([^)]*\)\s*$", "", text).strip()
        if text and not text.startswith("n("):
            return text
    return None