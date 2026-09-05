"""Parsing and judging of user answers against the SymPy-computed expected value.

The generic core shared by every topic: answer parsing, numeric/exact equivalence,
and step-by-step work checking (``analyze_work``). Probability's multi-part
grading lives in ``grader.probability``.
"""
import math
import re as _re

from sympy import E, Expr, I, N, Symbol, binomial, im, latex, oo, pi, re, simplify, sqrt
from sympy import solve as sym_solve
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from ..solver import solve


_LOCAL = {
    "I": I, "i": I, "pi": pi, "e": E, "sqrt": sqrt, "binomial": binomial,
    # ODE arbitrary constants: without these, SymPy's implicit-multiplication
    # parser splits "C1"/"C2" into "C*1"/"C*2" (a letter+trailing-digit token
    # is treated as implicit multiplication, not a single symbol name).
    "C1": Symbol("C1"), "C2": Symbol("C2"), "C3": Symbol("C3"),
}
_TRANS = standard_transformations + (implicit_multiplication_application, convert_xor)

_DEFAULT_TOL = 1e-4

# Leading limit notation from the OCR, e.g. "lim_{x -> -2} (x^2-4)/(x+2)" or
# "lim(x->-2) (x^2-4)/(x+2)" or "lim_{x \to -2} (...)": strip it so the
# expression itself can be parsed and checked.
_LIM_PREFIX = _re.compile(
    r"^\s*lim\s*(?:"
    r"_\s*\{\s*[A-Za-z]\s*(?:->|→|\\to)\s*[^}]+\}\s*|"
    r"\(\s*[A-Za-z]\s*(?:->|→|\\to)\s*[^)]+\)\s*"
    r")?"
)

# Probability "C(6,2)"-style combination notation -> SymPy binomial. Only
# matches integer-argument C(,) tokens, so a lone "+C" (integration constant)
# is never touched.
_COMB_NOTATION = _re.compile(r"\bC\(\s*(\d+)\s*,\s*(\d+)\s*\)")

def parse_answer(text):
    text = text.strip()
    if not text:
        raise ValueError("empty answer")
    text = (
        text.replace("π", "pi")
        .replace("×", "*")
        .replace("÷", "/")
        .replace("–", "-")
        .replace("−", "-")
        .replace("∞", "oo")
    )
    text = _LIM_PREFIX.sub("", text)
    # OCR sometimes concatenates an ODE arbitrary constant directly onto the
    # following function name ("C1cos(x)", "C2sin(x)") with no space. Without
    # a space, sympy's implicit-multiplication parser can't tell "C1cos" is
    # meant as C1 * cos and instead shatters the whole run into single-letter
    # symbols (C*1*c*o*s), so insert the boundary explicitly.
    text = _re.sub(r"\b(C[123])(?=[A-Za-z])", r"\1 ", text)
    # A leaked LaTeX exponent group ("e^{2x}") must become parenthesized
    # ("e^(2x)"), not bare ("e^2x") — Python/sympy's "^" binds to only the
    # next token, so "e^2x" parses as (e^2)*x, silently changing the meaning
    # of every multi-character exponent (a very common ODE/exponential shape).
    text = _re.sub(r"\^\s*\{([^{}]*)\}", r"^(\1)", text)
    text = _re.sub(r"√\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", text)
    text = text.replace("√", "sqrt")
    text = _COMB_NOTATION.sub(r"binomial(\1, \2)", text)
    text = _re.sub(r"\binf(?:inity)?\b", "oo", text)
    try:
        return parse_expr(text, local_dict=_LOCAL, transformations=_TRANS)
    except Exception:
        # The OCR "raw_text" final answer is meant to be the bare value (e.g.
        # "36"), but the model sometimes echoes the whole equation instead
        # (e.g. "AB.AC=36"), which isn't parseable as-is (dot-product notation
        # reads as a Python attribute access). Retry with just the RHS of the
        # last "=" before giving up — this only fires on a parse failure, so a
        # deliberately equation-shaped answer that parses fine is untouched.
        if "=" in text:
            rhs = text.rsplit("=", 1)[1].strip()
            if rhs:
                return parse_expr(rhs, local_dict=_LOCAL, transformations=_TRANS)
        raise

def _numeric_close(user, expected, tol):
    try:
        u = N(user)
        e = N(expected)
        if u.is_real and e.is_real:
            return abs(float(u) - float(e)) <= tol
        dr = float(N(re(user) - re(expected)))
        di = float(N(im(user) - im(expected)))
        return abs(dr) <= tol and abs(di) <= tol
    except (TypeError, ValueError):
        return False

def _angle_close(user, expected, tol):
    d = float(N(user - expected))
    d = (d + math.pi) % (2 * math.pi) - math.pi
    return abs(d) <= tol

# --- hybrid equivalence (CAS + numeric safety net) ---
#
# `simplify` is not a decision procedure: exotic equivalent forms (trig/exponential
# disguises) can fail to reduce to 0 / "no variable". The ladder below escalates
# only when needed: exact simplify, trig-intensified simplify (fu), then numeric
# sampling at deliberately non-special points (0.37, 1.23, ... — two non-equal
# high-school expressions agreeing at all of them is effectively impossible).

_SAMPLE_POINTS = (0.37, 1.23, 2.71, 3.87, 5.03)
_SAMPLE_TOL = 1e-6

def _sample_values(expr, var):
    """Evaluate expr at the sample points, skipping poles/non-real results."""
    vals = []
    for p in _SAMPLE_POINTS:
        try:
            v = N(expr.subs(var, p))
        except Exception:
            continue
        if not v.is_real or not v.is_finite:
            continue
        vals.append(float(v))
    return vals

def _equivalent_const(value, expected, var, diff=None):
    """True when value == expected + constant (in var) — the rule for any
    antiderivative line (constants cancel in F(b) − F(a))."""
    try:
        if diff is None:
            diff = simplify(value - expected)
        if not diff.has(var):
            return True
        if not simplify(diff, fu=True).has(var):
            return True
        vals = _sample_values(diff, var)
        return len(vals) >= 3 and all(abs(v - vals[0]) <= _SAMPLE_TOL for v in vals[1:])
    except Exception:
        return False

def _equivalent_exact(value, expected, var, diff=None):
    """True when value == expected exactly, via the same hybrid ladder."""
    try:
        if value == expected:
            return True
        if diff is None:
            diff = simplify(value - expected)
        if diff == 0:
            return True
        if simplify(diff, fu=True) == 0:
            return True
        vals = _sample_values(diff, var)
        return len(vals) >= 3 and all(abs(v) <= _SAMPLE_TOL for v in vals)
    except Exception:
        return False

def _is_given_restatement(lhs: str) -> bool:
    return lhs.strip().lower() in ("z", "z bar", "z_bar", "z̄")

_AT_POINT_RE = _re.compile(r"\bat\s+[A-Za-z]\w*\s*$", _re.I)

def _is_point_label(lhs: str) -> bool:
    """A trailing 'at x'/'at t' right before '=' names the point a section is
    about ('1. Value of the Function at x = 0', 'Tangent at x = 2') — a title,
    not a new assertion. Naming the point this way is common across topics, so
    this isn't continuity-specific."""
    return bool(_AT_POINT_RE.search(lhs.strip()))

def _is_equation_restatement(text, given_equations) -> bool:
    """True when some adjacent pair of "="-separated segments of `text` is
    the same equation as one of `given_equations` (either orientation) — a
    restated setup equation, not a computed value. Every adjacent pair is
    tried (not just the whole line's first/last segment), so a chain like
    "y'(0) = C2 - C1 = 2" matches on its middle-to-last segment even though
    its first segment ("y'(0)") is just a label. A pair that fails to parse
    (e.g. one straddling a "=>" arrow) is simply skipped."""
    segments = text.split("=")
    for j in range(len(segments) - 1):
        for k in range(j + 1, len(segments)):
            try:
                lhs_expr = parse_answer(segments[j])
                rhs_expr = parse_answer(segments[k])
            except Exception:
                continue
            if any(
                (simplify(lhs_expr - geq.lhs) == 0 and simplify(rhs_expr - geq.rhs) == 0)
                or (simplify(lhs_expr - geq.rhs) == 0 and simplify(rhs_expr - geq.lhs) == 0)
                for geq in given_equations
            ):
                return True
    return False


def _given_match(value, given) -> bool:
    """True when `value` structurally equals `given`, or (for symbolic values,
    e.g. a restated piecewise branch expression) is equivalent under simplify."""
    try:
        if value == given:
            return True
    except Exception:
        pass
    try:
        return simplify(value - given) == 0
    except Exception:
        return False

# ---------------------------------------------------------------------------
# answer_kind judging (function study & other study-style topics)
#
# Function-study answers aren't plain numbers: they're intervals (domain),
# categorical words (odd/even, increasing, sign), one-sided infinities
# (limits), or line equations in x and y (tangents). Each kind gets its own
# judge; `_judge_by_kind` dispatches. `exact_only` disables the numeric
# tolerance path (MoEYS wants exact log/fraction forms for areas). The judges
# return (correct, reason, note) — `note` carries a gentle coaching hint.
# ---------------------------------------------------------------------------

_IV_RE = _re.compile(
    r"(?P<l>[\(\]\[])\s*(?P<lo>-?\d+(?:\.\d+)?|oo|-oo)"
    r"\s*(?:[,;])\s*"
    r"(?P<hi>-?\d+(?:\.\d+)?|oo|-oo)\s*(?P<r>[\)\]\[])")
_DOMAIN_LABEL_RE = _re.compile(r"^[Dd][A-Za-z_]*\s*=\s*")
_XIN_RE = _re.compile(r"^[xX]\s*(?:∈|in)\s*")
_SETMINUS_RE = _re.compile(r"^[Rℝ]\s*(?:\\|/)?\s*\{\s*(?P<pt>-?\d+(?:\.\d+)?)\s*\}$")
_IV_INEQ_RE = _re.compile(
    r"^\s*(?P<lo>-?\d+(?:\.\d+)?|oo|-oo)\s*<\s*[xX]\s*<\s*(?P<hi>-?\d+(?:\.\d+)?|oo|-oo)\s*$")
_LEAD_EQ_RE = _re.compile(r"^[A-Za-z']+\s*(?:\([^)]*\))?\s*=\s*")

def _strip_lead(text):
    """Drop a leading 'lim_{...}' clause and/or a 'name =' / 'name(x) =' prefix
    so judges see the value itself ('lim g(x) = -∞' -> '-∞')."""
    text = text.strip()
    text = _LIM_PREFIX.sub("", text)
    return _LEAD_EQ_RE.sub("", text).strip()

def _bound_float(v):
    if isinstance(v, str):
        v = v.strip().lower().replace("oo", "inf")
        if v in ("inf", "+inf", "infinity"):
            return float("inf")
        if v in ("-inf", "-infinity"):
            return float("-inf")
    return float(v)

def _iv_dict(l_ch, lo, hi, r_ch):
    return {
        "lo": _bound_float(lo),
        "hi": _bound_float(hi),
        "lo_open": l_ch in "(]",
        "hi_open": r_ch in ")[",
    }

def _parse_interval(text):
    """Parse a domain answer into a list of interval dicts {lo, hi, lo_open,
    hi_open} (bounds as floats, ±inf allowed). Accepts international and French
    brackets, unions ('(-∞,-3) ∪ (3,∞)'), and 'ℝ\\{2}' set-minus notation."""
    text = text.strip()
    text = text.replace("∞", "oo").replace("−", "-").replace("–", "-")
    text = _re.sub(r"\binf(?:inity)?\b", "oo", text)
    text = _DOMAIN_LABEL_RE.sub("", text)
    text = _XIN_RE.sub("", text)
    m = _SETMINUS_RE.match(text)
    if m:
        p = _bound_float(m.group("pt"))
        return [
            {"lo": float("-inf"), "hi": p, "lo_open": True, "hi_open": True},
            {"lo": p, "hi": float("inf"), "lo_open": True, "hi_open": True},
        ]
    m = _IV_INEQ_RE.match(text)
    if m:
        return [_iv_dict("(", m.group("lo"), m.group("hi"), ")")]
    text = text.replace("∪", " , ").replace(" u ", " , ").replace(" U ", " , ")
    ivs = [_iv_dict(m.group("l"), m.group("lo"), m.group("hi"), m.group("r"))
           for m in _IV_RE.finditer(text)]
    return ivs or None

def _iv_close(a, b, tol):
    return (a == b == float("inf")) or (a == b == float("-inf")) or abs(a - b) <= tol

def _judge_interval(expected, user_answer, tol):
    user = _parse_interval(user_answer)
    if user is None or len(user) != len(expected):
        return False, "mismatch", None
    for u, e in zip(user, expected):
        if not _iv_close(u["lo"], _bound_float(e["lo"]), tol):
            return False, "mismatch", None
        if not _iv_close(u["hi"], _bound_float(e["hi"]), tol):
            return False, "mismatch", None
        if u["lo_open"] != e["lo_open"] or u["hi_open"] != e["hi_open"]:
            return False, "mismatch", None
    return True, "exact", None

_KH = "\u1780-\u17ff"

def _norm_choice(text):
    text = text.strip().lower()
    text = _re.sub(rf"[^a-z{_KH}]+", " ", text)
    return " ".join(text.split())

def _judge_choice(expected, choices, user_answer):
    entry = (choices or {}).get(expected) or {}
    norm = _norm_choice(user_answer)
    for w in entry.get("words") or []:
        if _norm_choice(w) == norm:
            return True, "exact", None
    # Accept the defining equation too (e.g. "g(-x) = -g(x)"), with a note to
    # write the word explicitly (MoEYS rubrics award the classification).
    n2 = _re.sub(r"[\s=]", "", user_answer.lower())
    for p in entry.get("phrases") or []:
        if _re.sub(r"[\s=]", "", p.lower()) == n2:
            return True, "exact", (
                "Correct condition — remember to write the word "
                "“អនុគមន៍សេស” explicitly on the exam for full marks."
            )
    return False, "mismatch", None

def _judge_infinity(expected, user_answer):
    try:
        value = parse_answer(_strip_lead(user_answer))
    except Exception:
        return False, "mismatch", None
    if value == expected and value in (oo, -oo):
        return True, "exact", None
    return False, "mismatch", None

def _judge_line(expected, user_answer, tol):
    """Tangent-line answers: 'y = 2x/3', '(2/3)x', point-slope, or the implicit
    form '3y - 2x = 0' — any equation of the same line."""
    text = _strip_lead(user_answer)
    x_sym, y_sym = Symbol("x"), Symbol("y")
    if "=" in text:
        lhs, _, rhs = text.partition("=")
        try:
            imp = simplify(parse_answer(lhs) - parse_answer(rhs))
        except Exception:
            return False, "mismatch", None
        try:
            sols = sym_solve(imp, y_sym) if imp.has(y_sym) else (sym_solve(imp, x_sym) if imp.has(x_sym) else [])
        except Exception:
            sols = []
        for s in sols:
            if _equivalent_exact(s, expected, x_sym) or _numeric_close(s, expected, tol):
                return True, "exact", None
        return False, "mismatch", None
    try:
        value = parse_answer(text)
    except Exception:
        return False, "mismatch", None
    if _equivalent_exact(value, expected, x_sym) or _numeric_close(value, expected, tol):
        return True, "exact", None
    return False, "mismatch", None

def _judge_expression(expected, user_answer, tol, exact_only=False):
    text = _strip_lead(user_answer)
    try:
        value = parse_answer(text)
    except Exception:
        return False, "mismatch", None
    var_sym = Symbol("x")
    if _equivalent_exact(value, expected, var_sym):
        return True, "exact", None
    if not exact_only and _numeric_close(value, expected, tol):
        return True, "numeric", None
    return False, "mismatch", None

def _judge_sign(expected, user_answer, tol):
    """Sign-of-g answer: expected is the list of positive interval dicts; the
    student's interval list is judged structurally (order/union tolerant)."""
    return _judge_interval(expected, user_answer, tol)


def _judge_monotonicity(expected, user_answer, tol):
    """Monotonicity answer: expected is a list of {interval, direction}. Correct
    when the student's text names each interval with the right direction word
    (កើន/croît/increasing vs ចុះ/décroît/decreasing)."""
    text = user_answer.lower()
    inc_kw = ["កើន", "cro", "incr", "increas", "ឡើង", "↗"]
    dec_kw = ["ចុះ", "décro", "decro", "decreas", "ធ្លាក់", "↘"]
    ok = True
    for piece in expected:
        iv = piece.get("interval", "")
        nums = _re.findall(r"-?\d+(?:\.\d+)?", iv)
        has_bounds = all(n in text.replace(" ", "") for n in nums) if nums else True
        kw = inc_kw if piece.get("direction") == "inc" else dec_kw
        has_kw = any(k in text for k in kw)
        if not (has_bounds and has_kw):
            ok = False
    return ok, "exact" if ok else "mismatch", None


_DISCONTINUOUS_RE = _re.compile(r"\b(discontinuous|non-?continuous|not\s+continuous)\b", _re.I)
_CONTINUOUS_RE = _re.compile(r"\bcontinuous\b", _re.I)

def _judge_continuity(expected, user_answer):
    """Continuity verdict answer: BAC II students write a full conclusion
    sentence ('...on peut dire que f est discontinue en x=1'-style, or 'In
    conclusion ... it is not continuous at x = 1'), not a bare value, so this
    scans the free text for the verdict instead of parsing it as math.
    'discontinuous' is checked first since it contains 'continuous' as a
    substring and 'not continuous' negates it — a plain \\bcontinuous\\b
    match after that filter is unambiguous."""
    text = user_answer or ""
    if _DISCONTINUOUS_RE.search(text):
        verdict = "discontinuous"
    elif _CONTINUOUS_RE.search(text):
        verdict = "continuous"
    else:
        return False, "mismatch", None
    ok = verdict == expected
    return ok, "exact" if ok else "mismatch", None


def _judge_variation_table(expected, user_answer, checkpoints, tol):
    """Variation-table answer: judged by whether the student's written lines
    contain every checkpoint value (g'(x) and the limits/extrema). Tolerant —
    the authoritative check is the any_order work analysis."""
    if not checkpoints:
        return False, "mismatch", None
    text = user_answer.replace(" ", "")
    ok = True
    for cp in checkpoints:
        v = cp["value"]
        if v in (oo, -oo):
            token = "∞" if v == oo else "-∞"
            if token not in user_answer and "infty" not in user_answer.lower() and "inf" not in user_answer.lower():
                ok = False
        else:
            vs = str(v)
            try:
                vsn = str(N(v, 6))
            except Exception:
                vsn = vs
            if vs not in text and vsn not in text:
                ok = False
    return ok, "exact" if ok else "mismatch", None


def _judge_study(kind, expected, user_answer, tol, checkpoints):
    if kind == "sign":
        return _judge_sign(expected, user_answer, tol)
    if kind == "monotonicity":
        return _judge_monotonicity(expected, user_answer, tol)
    return _judge_variation_table(expected, user_answer, checkpoints, tol)


def _judge_by_kind(kind, expected, user_answer, tol=_DEFAULT_TOL, choices=None, exact_only=False, checkpoints=None):
    """Dispatch an answer to the right shape judge (interval/choice/infinity/
    line/expression/study-tables). Returns (correct, reason, note)."""
    if kind == "interval":
        return _judge_interval(expected, user_answer, tol)
    if kind == "choice":
        return _judge_choice(expected, choices, user_answer)
    if kind == "infinity":
        return _judge_infinity(expected, user_answer)
    if kind == "line":
        return _judge_line(expected, user_answer, tol)
    if kind in ("sign", "monotonicity", "variation_table"):
        return _judge_study(kind, expected, user_answer, tol, checkpoints)
    if kind == "continuity":
        return _judge_continuity(expected, user_answer)
    return _judge_expression(expected, user_answer, tol, exact_only)

def _match_checkpoint(value, cp, tol, var_sym):
    """Line-check matcher for one checkpoint. Non-SymPy checkpoint values
    (interval/choice structures) can't be verified from an OCR line — skip them
    rather than flagging; ±oo checkpoints match only the same infinity."""
    cv = cp["value"]
    if isinstance(cv, (str, list, dict, bool)) or not isinstance(cv, (int, float, Expr)):
        return False
    if cv in (oo, -oo):
        return value in (oo, -oo) and value == cv
    try:
        if simplify(value - cv) == 0:
            return True
    except Exception:
        return False
    if _numeric_close(value, cv, tol):
        return True
    if cp.get("constant_ok"):
        try:
            return _equivalent_const(value, cv, var_sym)
        except Exception:
            return False
    return False

def analyze_work(topic, question_type, params, lines, tolerance=None) -> dict:
    """Deterministically check each line of a student's work against the SymPy-computed
    checkpoints for this solution. Returns the first line whose claimed value
    doesn't match the correct value at that point in the solution — a verified fact, not
    an LLM guess. Lines that don't parse, or that just restate the given z, are skipped
    rather than flagged (SymPy can't judge a definition, only a computation).

    Every checkpoint also carries the `formula` it exercises, so the same pass yields
    `formula_breakdown` — per-formula reached/missed data used for weakness stats.

    Matching strategy is per-topic via the solution's `work_mode`:
      - default (complex, limits, integrals, ...): strict sequential pointer — a
        line is checked against the next expected checkpoint in order.
      - "any_order" (probability): a line matches any checkpoint value (exact, then
        numeric), so the natural count/ratio ordering and repeated-equivalent
        expansion lines all verify; formula-definition and jot lines (symbolic or
        non-real values) are skipped rather than flagged.
    """
    tol = tolerance if tolerance is not None else _DEFAULT_TOL
    solution = solve(topic, question_type, params)
    if solution.get("work_mode") == "any_order":
        return _analyze_work_any_order(solution, params, lines, tol)
    given_expr = solution.get("given")
    given_expressions = solution.get("given_expressions") or []
    given_equations = solution.get("given_equations") or []
    checkpoints = list(solution.get("checkpoints", []))
    if not checkpoints or checkpoints[-1]["value"] != solution["answer_exact"]:
        checkpoints.append({"label": "final answer", "value": solution["answer_exact"], "formula": None})

    line_results = []
    pointer = 0
    first_error_line = None
    matched_checkpoints = set()

    var_sym = Symbol(params.get("var", "x"))
    for i, raw in enumerate(lines, 1):
        text = raw.strip()
        if not text:
            continue

        # A continuity conclusion line ("...so f is discontinuous at x=2")
        # often restates the join point as "x = 2" — parsing the tail after
        # "=" would check that point value against a checkpoint it was never
        # meant to match. The verdict itself is graded separately (against
        # answer_kind "continuity"); here it's a restatement, not a computed
        # checkpoint, so skip it rather than flag it wrong.
        if _CONTINUOUS_RE.search(text) or _DISCONTINUOUS_RE.search(text):
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "conclusion"})
            continue

        had_equals = "=" in text
        if had_equals:
            lhs, _, value_str = text.rpartition("=")
            if _is_given_restatement(lhs) or _is_point_label(lhs):
                line_results.append({"line": i, "text": raw, "checked": False, "reason": "given"})
                continue
        else:
            value_str = text

        # A "±"/"∓" line (e.g. "r = 1 ± i") compactly asserts a *pair* of
        # values (both characteristic roots at once) rather than one — SymPy's
        # parser otherwise reads "±" as a bare symbol name, turning "1±i" into
        # the nonsense expression "I*±" instead of raising, which would then
        # be checked (and fail) against a single checkpoint. Try both signs
        # against the next two checkpoints as a pair before falling through
        # to the normal single-value path.
        if "±" in value_str or "∓" in value_str:
            flip = "∓" in value_str
            plus_str = value_str.replace("±", "+").replace("∓", "-" if flip else "+")
            minus_str = value_str.replace("±", "-").replace("∓", "+" if flip else "-")
            try:
                v_plus = parse_answer(plus_str)
                v_minus = parse_answer(minus_str)
            except Exception:
                line_results.append({"line": i, "text": raw, "checked": False, "reason": "unparsed"})
                continue
            pair_idx = None
            for idx in range(pointer, len(checkpoints) - 1):
                a, b = checkpoints[idx], checkpoints[idx + 1]
                if (
                    (_match_checkpoint(v_plus, a, tol, var_sym) and _match_checkpoint(v_minus, b, tol, var_sym))
                    or (_match_checkpoint(v_minus, a, tol, var_sym) and _match_checkpoint(v_plus, b, tol, var_sym))
                ):
                    pair_idx = idx
                    break
            if pair_idx is not None:
                matched_checkpoints.update({pair_idx, pair_idx + 1})
                line_results.append({
                    "line": i,
                    "text": raw,
                    "checked": True,
                    "correct": True,
                    "matches": checkpoints[pair_idx]["label"],
                    "formula": checkpoints[pair_idx].get("formula"),
                    "expected": f"{checkpoints[pair_idx]['value']}, {checkpoints[pair_idx + 1]['value']}",
                })
                pointer = pair_idx + 2
                continue
            target = checkpoints[pointer] if pointer < len(checkpoints) else None
            line_results.append({
                "line": i,
                "text": raw,
                "checked": True,
                "correct": False,
                "formula": target.get("formula") if target else None,
                "expected": str(target["value"]) if target else None,
            })
            if first_error_line is None:
                first_error_line = i
            continue

        try:
            value = parse_answer(value_str)
        except Exception:
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "unparsed"})
            continue

        if given_expr is not None and value == given_expr:
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "given"})
            continue

        # A line ending in a bare combination of ODE arbitrary constants
        # ("y(0) = ... = C1", "y'(0) = ... = C1 + C2") labels an intermediate
        # result for the *next* line to resolve numerically ("C1 = 1",
        # "1 + C2 = 1 => C2 = 0") rather than asserting a value itself — this
        # is the common ODE pattern of deferring the numeric solve to its own
        # line. Skip it rather than checking the symbolic combination against
        # the numeric checkpoint it's a placeholder for.
        _ode_consts = {Symbol("C1"), Symbol("C2"), Symbol("C3")}
        try:
            is_const_combo = bool(value.free_symbols) and value.free_symbols <= _ode_consts
        except AttributeError:
            is_const_combo = False
        if is_const_combo:
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "label"})
            continue

        # A symbolic value (free variable still present) that matches one of
        # the problem's own given expressions (e.g. continuity's piecewise
        # branch formulas) is a restatement of the setup, not a computed
        # checkpoint — never a concrete number, so this can't shadow a real
        # numeric checkpoint match below.
        try:
            symbolic_value = bool(value.free_symbols)
        except AttributeError:
            symbolic_value = False
        if symbolic_value and given_expressions and any(_given_match(value, g) for g in given_expressions):
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "given"})
            continue

        # A bare line with no "=" that parses to a free-standing symbolic
        # expression (e.g. "AB x AC" as a section header announcing the next
        # computation) isn't an asserted value — skip it rather than flagging
        # it wrong against whatever checkpoint comes next. Lines that DO use
        # "=" still get checked normally even if symbolic (e.g. "f'(x) = ...").
        if not had_equals:
            try:
                if bool(value.free_symbols):
                    line_results.append({"line": i, "text": raw, "checked": False, "reason": "label"})
                    continue
            except AttributeError:
                pass

        # Try the immediately-next checkpoint first. Only if that fails do we
        # consider the line a restatement of a given equation (e.g. the
        # characteristic equation "r^2 - 2r + 2 = 0", or an IC substitution
        # "y'(0) = C2 - C1 = 2") — checked here, before scanning further
        # ahead, so a trivial trailing value like the "0" in "... = 0" can't
        # accidentally match some unrelated later checkpoint that happens to
        # equal 0/1/etc. and derail the pointer past checkpoints the student
        # never actually asserted. A line that fails both still gets one more
        # chance against later checkpoints, so genuinely skipped-ahead work
        # (an intermediate line the student omitted) still verifies.
        matched_idx = None
        if pointer < len(checkpoints) and _match_checkpoint(value, checkpoints[pointer], tol, var_sym):
            matched_idx = pointer
        elif had_equals and given_equations and _is_equation_restatement(text, given_equations):
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "given"})
            continue
        else:
            for idx in range(pointer + 1, len(checkpoints)):
                if _match_checkpoint(value, checkpoints[idx], tol, var_sym):
                    matched_idx = idx
                    break

        if matched_idx is not None:
            label = checkpoints[matched_idx]["label"]
            matched_checkpoints.add(matched_idx)
            line_results.append({
                "line": i,
                "text": raw,
                "checked": True,
                "correct": True,
                "matches": label,
                "formula": checkpoints[matched_idx].get("formula"),
                "expected": str(checkpoints[matched_idx]["value"]),
            })
            pointer = matched_idx + 1
        elif pointer > 0 and _match_checkpoint(value, checkpoints[pointer - 1], tol, var_sym):
            # Restates a value already reached (e.g. an unevaluated expression
            # line immediately followed by its evaluated form) — not a new
            # checkpoint, but not an error either.
            line_results.append({
                "line": i,
                "text": raw,
                "checked": True,
                "correct": True,
                "matches": checkpoints[pointer - 1]["label"],
                "formula": checkpoints[pointer - 1].get("formula"),
                "expected": str(checkpoints[pointer - 1]["value"]),
                "restated": True,
            })
        else:
            target = checkpoints[pointer] if pointer < len(checkpoints) else None
            line_results.append({
                "line": i,
                "text": raw,
                "checked": True,
                "correct": False,
                "formula": target.get("formula") if target else None,
                "expected": str(target["value"]) if target else None,
            })
            if first_error_line is None:
                first_error_line = i

    formula_breakdown = []
    for idx, cp in enumerate(checkpoints):
        if cp.get("formula"):
            formula_breakdown.append({
                "formula": cp["formula"],
                "label": cp["label"],
                "reached": idx in matched_checkpoints,
                "line": next((r["line"] for r in line_results if r.get("matches") == cp["label"]), None),
            })

    return {
        "line_results": line_results,
        "first_error_line": first_error_line,
        "reached_final_answer": pointer >= len(checkpoints),
        "formula_breakdown": formula_breakdown,
    }

def _analyze_work_any_order(solution, params, lines, tol):
    """Probability's work-checking mode.

    Matches each line against ANY checkpoint value (exact, then numeric) instead
    of a strict sequence, so students writing the natural count/ratio order, or
    chains of equivalent expansion lines (`= 10 * 5 = 50`), all verify. Lines that
    parse to a symbolic expression (formula definitions like (n!)/(r!(n-r)!)) or
    to a non-real value (jot lines like "7 7 1,3,5,7") are skipped rather than
    flagged — they're restatements, not computations. The authoritative verdicts
    are the per-part final answers from `grade`/`grade_part`; this only drives
    the red-pen overlay and formula_breakdown."""
    given_expr = solution.get("given")
    checkpoints = list(solution.get("checkpoints", []))
    if not checkpoints or checkpoints[-1]["value"] != solution["answer_exact"]:
        checkpoints.append({"label": "final answer", "value": solution["answer_exact"], "formula": None})

    line_results = []
    first_error_line = None
    matched_checkpoints = set()

    for i, raw in enumerate(lines, 1):
        text = raw.strip()
        if not text:
            continue
        if "=" in text:
            lhs, _, value_str = text.rpartition("=")
            if _is_given_restatement(lhs):
                line_results.append({"line": i, "text": raw, "checked": False, "reason": "given"})
                continue
        else:
            value_str = text
        try:
            value = parse_answer(value_str)
        except Exception:
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "unparsed"})
            continue
        if given_expr is not None and value == given_expr:
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "given"})
            continue
        # Symbolic or non-real lines are formula definitions / jotted sets, not
        # computed checkpoints — never mark them wrong.
        try:
            symbolic = bool(value.free_symbols) or not value.is_number or value.is_real is False
        except AttributeError:
            symbolic = True  # e.g. parse returned a plain tuple from "7 7 1,3,5,7"
        if symbolic:
            line_results.append({"line": i, "text": raw, "checked": False, "reason": "symbolic"})
            continue

        best_idx = None
        var_sym = Symbol(params.get("var", "x"))
        for idx, cp in enumerate(checkpoints):
            if _match_checkpoint(value, cp, tol, var_sym):
                best_idx = idx
                break
        if best_idx is not None:
            matched_checkpoints.add(best_idx)
            line_results.append({
                "line": i,
                "text": raw,
                "checked": True,
                "correct": True,
                "matches": checkpoints[best_idx]["label"],
                "formula": checkpoints[best_idx].get("formula"),
                "expected": str(checkpoints[best_idx]["value"]),
            })
        else:
            line_results.append({
                "line": i,
                "text": raw,
                "checked": True,
                "correct": False,
                "formula": None,
                "expected": None,
            })
            if first_error_line is None:
                first_error_line = i

    formula_breakdown = []
    for idx, cp in enumerate(checkpoints):
        if cp.get("formula"):
            formula_breakdown.append({
                "formula": cp["formula"],
                "label": cp["label"],
                "reached": idx in matched_checkpoints,
                "line": next((r["line"] for r in line_results if r.get("matches") == cp["label"]), None),
            })

    return {
        "line_results": line_results,
        "first_error_line": first_error_line,
        "reached_final_answer": len(matched_checkpoints) >= len(checkpoints),
        "formula_breakdown": formula_breakdown,
    }

def grade_part(topic, question_type, params, label, user_answer, tolerance=None):
    """Grade one sub-part of a multi-part exercise (the progressive flow: check
    A, then B, then C). Accepts a bare value or a label-prefixed value."""
    from .probability import _judge_value

    solution = solve(topic, question_type, params)
    part = next((p for p in solution.get("parts", []) if p["label"] == label), None)
    if part is None:
        raise ValueError(f"unknown part label: {label}")
    m = _re.match(rf"^\s*{_re.escape(str(label))}\s*[:=]\s*(.+)$", user_answer)
    if m:
        user_answer = m.group(1)
    expected = part["answer_exact"]
    display = part.get("answer_display") or str(expected)
    try:
        correct, reason, note = _judge_value(
            expected, user_answer,
            tolerance if tolerance is not None else _DEFAULT_TOL,
            kind=part.get("answer_kind"), choices=part.get("choices"),
            exact_only=part.get("exact_only"), checkpoints=part.get("checkpoints"),
        )
    except Exception as exc:
        correct, reason, note = False, f"could not parse answer: {exc}", None
    try:
        given = str(parse_answer(user_answer))
    except Exception:
        given = user_answer.strip()
    verdict = {
        "label": label,
        "correct": correct,
        "reason": reason,
        "given": given,
        "expected": display,
        "answer_decimal": part["answer_decimal"],
    }
    if note:
        verdict["note"] = note
    if not isinstance(expected, (list, dict, str)):
        expected_latex = part.get("answer_latex") or latex(expected)
    else:
        expected_latex = part.get("answer_latex") or display
    return {
        **verdict,
        "part": label,
        "parts": [verdict],
        "expected_latex": expected_latex,
        "steps": solution["steps"],
        "graph": solution.get("graph"),
        "all_complete": correct and str(solution.get("target_label")) == str(label),
    }

def grade(topic, question_type, params, user_answer, tolerance=None):
    tol = tolerance if tolerance is not None else _DEFAULT_TOL
    solution = solve(topic, question_type, params)
    expected = solution["answer_exact"]

    kind = solution.get("answer_kind")
    if kind:
        # Word-heavy / non-numeric answers (domain intervals, odd/even/sign
        # classifications, monotonicity, variation tables, tangent lines,
        # one-sided infinities): dispatch to the same deterministic shape
        # judges function-study parts use, rather than forcing the answer
        # through SymPy's expression parser. Any topic's solver can opt in by
        # setting "answer_kind" (+ "choices"/"exact_only" as needed) on its
        # solve() output — no plumbing beyond this.
        try:
            verdict, reason, note = _judge_by_kind(
                kind, expected, user_answer, tol,
                choices=solution.get("choices"),
                exact_only=solution.get("exact_only", False),
                checkpoints=solution.get("checkpoints"),
            )
        except Exception as exc:
            return {
                "correct": False,
                "reason": f"could not parse answer: {exc}",
                "given": user_answer,
                "expected": str(expected),
                "answer_decimal": solution["answer_decimal"],
                "steps": solution["steps"],
            }
        try:
            given = str(parse_answer(user_answer))
        except Exception:
            given = user_answer.strip()
        display = solution.get("answer_display") or str(expected)
        if not isinstance(expected, (list, dict, str)):
            expected_latex = solution.get("answer_latex") or latex(expected)
        else:
            expected_latex = solution.get("answer_latex") or display
        result = {
            "correct": verdict,
            "reason": reason,
            "given": given,
            "expected": display,
            "expected_latex": expected_latex,
            "answer_decimal": solution["answer_decimal"],
            "steps": solution["steps"],
            "graph": solution.get("graph"),
        }
        if note:
            result["note"] = note
        return result

    try:
        user = parse_answer(user_answer)
    except Exception as exc:
        return {
            "correct": False,
            "reason": f"could not parse answer: {exc}",
            "given": user_answer,
            "expected": str(expected),
            "answer_decimal": solution["answer_decimal"],
            "steps": solution["steps"],
        }

    var_sym = Symbol(params.get("var", "x"))
    if question_type == "indefinite_integral":
        # Any F(x) + constant is a valid antiderivative — decide here alone,
        # never fall through to the numeric branches (symbolic F can't be
        # converted to a float).
        verdict = _equivalent_const(user, expected, var_sym)
        reason = "indefinite" if verdict else "mismatch"
    elif _equivalent_exact(user, expected, var_sym):
        verdict, reason = True, "exact"
    elif question_type == "argument" and _angle_close(user, expected, tol):
        verdict, reason = True, "numeric"
    elif _numeric_close(user, expected, tol):
        verdict, reason = True, "numeric"
    else:
        verdict, reason = False, "mismatch"

    return {
        "correct": verdict,
        "reason": reason,
        "given": str(user),
        "expected": str(expected),
        "expected_latex": latex(expected),
        "answer_decimal": solution["answer_decimal"],
        "steps": solution["steps"],
        "graph": solution.get("graph"),
    }