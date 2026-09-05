"""Function-study drawing checks.

The hand-drawn graph cannot be OCR-graded (OCR reads text, not ink), so we
verify the *labels/annotations* the student writes on their drawing — the
asymptote equations (x = -3, x = 3), the tangent equation, and named points
(the origin). Absence is never marked wrong: the checklist is informational
partial credit shown next to the reference graph, and the curve itself is
always verified against the reference the student can see.
"""
import re

from sympy import Rational, Symbol, diff, simplify, sympify

from ...core.grading import analyze_work, grade, grade_part, parse_answer
from ...core.shared import _calc_locals

__all__ = ["analyze_work", "grade", "grade_graph_check", "grade_part", "parse_answer"]


def _fmt(v):
    if isinstance(v, Rational):
        return str(v.p) if v.q == 1 else f"{v.p}/{v.q}"
    v = float(v)
    return str(int(v)) if v == int(v) else f"{v:g}"


def _asym_pattern(xv):
    """A regex matching 'x = a' (or 'x:a', 'x=-3') written on the drawing. The
    sign matters: 'x = 3' must not satisfy the 'x = -3' asymptote check."""
    if float(xv) < 0:
        return rf"x\s*[=:]\s*-\s*{abs(float(xv)):g}\b"
    return rf"x\s*[=:]\s*(?<![-\d]){float(xv):g}\b"


def _line_pattern(label):
    """Regex for a written oblique/horizontal asymptote label like 'y = x+1'
    or 'y = x/2' or 'y = -1'. Both label and text are space-normalized and use
    ASCII hyphens before matching."""
    s = label.strip().replace(" ", "").replace("−", "-").replace("–", "-")
    return re.escape(s)


def _slope_pattern(m):
    n, d = m.as_numer_denom()
    pats = [
        rf"{n}x?/{d}",
        rf"\(?{n}/{d}\)?\s*x\b",
    ]
    try:
        dec = f"{float(m):.4f}".rstrip("0").rstrip(".")
        if len(dec) >= 3:
            pats.append(re.escape(dec))
    except Exception:
        pass
    return "|".join(pats)


def grade_graph_check(params, lines):
    """Scan the student's written/OCR'd lines for the key labels of a correct
    drawing: vertical asymptotes, the tangent line, and named points. Returns
    {items, found, total} — purely informational, never a pass/fail verdict."""
    graph = params.get("graph") or {}
    var = params.get("var", "x")
    text = "\n".join(lines or [])
    text = text.replace("−", "-").replace("–", "-")
    items = []

    for a in graph.get("asymptotes", []):
        if a.get("kind") == "vertical":
            xv = a["x"]
            found = re.search(_asym_pattern(xv), text) is not None
            items.append({"label": f"x = {_fmt(xv)}", "found": found})
            continue
        if a.get("kind") not in ("oblique", "horizontal"):
            continue
        label = a.get("label") or a.get("line") or ""
        if not label:
            continue
        pattern = _line_pattern(label)
        found = bool(re.search(pattern, text.replace(" ", "")))
        items.append({"label": label, "found": found})

    t = graph.get("tangent")
    if t:
        expr = sympify(params.get("function_expr"), locals=_calc_locals(var))
        x = Symbol(var)
        x0 = sympify(t["x0"], locals=_calc_locals(var))
        m = simplify(diff(expr, x).subs(x, x0))
        found = bool(re.search(_slope_pattern(m), text))
        items.append({"label": f"T: y = {_fmt(m)} x", "found": found})

    for p in graph.get("points", []):
        lab = p.get("label", "")
        if not lab:
            continue
        found = bool(re.search(rf"\b{re.escape(lab)}\b", text)) or \
            bool(re.search(rf"\(\s*0\s*,\s*0\s*\)", text))
        items.append({"label": lab, "found": found})

    return {"items": items, "found": sum(1 for it in items if it["found"]), "total": len(items)}