"""Deterministic, step-by-step points rubric toolkit — generalizes the
marking scheme built for the 2018 past exam (``engine/topics/past_exam/rubric.py``)
to every topic's live/generated questions, not just that one exam.

Each topic owns its scoring rules in ``engine/topics/<topic>/rubric.py``
(routed by ``engine/rubric.py``); this module holds the shared machinery
they build on — matching a value to a step, the point split, and the
policy-driven matcher `score_rubric` — and the default policy
(`default_score_work`) the topics without rules of their own reuse.

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

from sympy import Add, Expr, Symbol, diff, fraction, oo, simplify, sympify

from .dispatch import solve
from .grading import (_angle_close, _equivalent_const, _equivalent_renamed, _numeric_close, _strip_khmer,
                      fill_prime_slots, grade, grade_part, parse_answer, prime_slots, with_method)

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


def step_matches(text, expected, tol=1e-4, constant_ok=False, var=None, angle=False, alternatives=None,
                 free_constants=None):
    """True when `text` (one student line) asserts the scalar/vector value
    `expected` (see `is_simple_value` — never called on a structured value).
    `constant_ok`/`var` mirror `analyze_work`'s own checkpoint flag: an
    indefinite-integral antiderivative line may differ from `expected` by
    any constant in `var` (F(x)+C is still correct for any C) — see
    `_equivalent_const`. `free_constants`: the step's arbitrary constants
    (an ODE general solution) may carry the student's own names — see
    `grading._equivalent_renamed`."""
    if alternatives:
        return any(step_matches(text, alt, tol, constant_ok, var, angle) for alt in [expected, *alternatives])
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
    if _scalar_matches(value, expected, tol, constant_ok, var):
        return True
    if free_constants and _equivalent_renamed(value, expected, free_constants, var or Symbol("x")):
        return True
    # Angle steps are equal mod 2pi (7pi/4 is the same argument as -pi/4).
    return angle and _angle_close(value, expected, tol)


def _scalar_matches(value, expected, tol, constant_ok=False, var=None):
    if expected in (oo, -oo):
        return value == expected
    try:
        if simplify(value - expected) == 0:
            return True
    except Exception:
        pass
    if constant_ok and var is not None:
        try:
            if _equivalent_const(value, expected, var):
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


def build_rubric(topic, question_type, params, question_points=DEFAULT_QUESTION_POINTS, part_label=None, method=None):
    """[{"item", "label", "value"|"kind", "points", "answer_kind", ...}] for
    one live/generated question, mechanically weighted per the module
    docstring's two rules. Never hand-typed — every value/kind comes
    straight from this exercise's own ``solve()`` output.

    `part_label`: for a multi-part exercise, restrict the rubric to just
    that one sub-part (A, B, ...) — used by the progressive check-each-part
    flow, where the student's `work_text` only ever contains that one
    part's canvas, so scoring the OTHER parts' checkpoints against it would
    always fail them (never actually attempted) instead of just not being
    part of this grading pass.

    `method`: one of the solution's blueprint methods (see
    ``engine/core/blueprints.py``) to build the rubric from; default is the
    solution's own checkpoints (its first method)."""
    solution = with_method(solve(topic, question_type, params), method)
    parts = solution.get("parts")
    if parts and part_label is not None:
        parts = [p for p in parts if p["label"] == part_label]
        if not parts:
            raise ValueError(f"unknown part label: {part_label}")
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
                "constant_ok": cp.get("constant_ok", False),
                "angle": cp.get("angle", False),
                "alternatives": cp.get("alternatives"),
                "free_constants": cp.get("free_constants"),
                "label_latex": cp.get("label_latex"),
                "subject": cp.get("subject"),
            })
    return rubric


# ---------------------------------------------------------------------------
# Scoring: match a student's full written work against the rubric.
# ---------------------------------------------------------------------------

def score_rubric(topic, question_type, params, rubric, lines, tolerance=None, *,
                 implied_credit=True, split_chains=False, term_credit=False,
                 prime_credit=False):
    """Match a student's full written work against `rubric` (from
    `build_rubric`). `lines`: the raw work, one asserted fact per line, any
    order. A "simple" step is matched against any not-yet-claimed line; a
    "judged" step (a structured final answer) is graded by trying
    `grade`/`grade_part` on each not-yet-claimed line, so it still benefits
    from those judges' own tolerant parsing.

    The two policy switches are each topic's call (its own
    ``engine/topics/<topic>/rubric.py``):

    `implied_credit`: a student who combines several checkpoints into one
    condensed line (writing `|z| = sqrt(144+25)` straight to the answer
    instead of separate `a^2 = 144` / `b^2 = 25` lines) has every earlier
    checkpoint in that same item implied by whichever later one a line DID
    match — the later value couldn't have been reached without them. So
    after the literal per-step matching pass, any of an item's checkpoints
    that sit before its own last actually-matched checkpoint are credited
    too, even with no line of their own — mirrors `analyze_work`'s own
    forward-matching leniency. A checkpoint AFTER the last real match earns
    nothing. Implied credit also needs the work to actually show a
    derivation (`_shows_work`): a bare final answer on its own earns only
    its own step, not the whole method it skipped. Off = full marks need
    every step shown.

    `split_chains`: match every "="-separated part of a line on its own
    (each part earns at most one step), so a line chaining several steps
    (`y' = 2x(x+3)(x+4) + x^2(2x+7) = 4x^3 + ...`) shows each of them. Off
    = a line is read by its last value only.

    `term_credit`: a derivative step (one whose rubric entry names the
    `subject` it differentiates) with no line of its own is still shown when
    the given is a sum with a term c*subject and a line writes c*step as a
    term of a sum — ``y = 4x + e^{-2x}``, ``y' = 4 - 2e^{-2x}`` shows
    ``(e^{-2x})' = -2e^{-2x}``; ``y = 2e^{3x} - 6x``, ``y' = 6e^{3x} - 6``
    shows ``(e^{3x})' = 3e^{3x}``. Only such terms count (never a value the
    line merely simplifies to, never a number that happens to appear), so a
    step that disappears into the simplified answer still has to be written.

    `prime_credit`: read ``(E)'`` as "the derivative of E", the way the
    chain/product rule is written out. A line part holding such slots is
    judged with each slot set to the true derivative; when that is a correct
    value (a step or the answer), the factor multiplying a slot is shown
    (``y' = -(sin(1/x))' * sin(sin(1/x))`` shows the outer derivative
    ``-sin(sin(1/x))``), and so is the slot's own value when the next "="
    part substitutes it (``(1/x)' * cos(1/x) = -1/x^2 cos(1/x)`` shows
    ``(1/x)' = -1/x^2``, but only if -1/x^2 really is (1/x)'; a correctly
    substituted quotient shows its numerator, u'v - uv').

    Returns {"earned", "possible", "breakdown"} — earned/possible are exact
    Fractions; never an LLM judgment call."""
    work = [ln.strip() for ln in lines if ln.strip()]
    if split_chains:
        parts = [(i, c.strip()) for i, raw in enumerate(work)
                 for c in (raw.split("=") if "=" in raw else [raw]) if c.strip()]
    else:
        parts = list(enumerate(work))
    part_used = [False] * len(parts)
    matched_line_idx = [None] * len(rubric)
    var_sym = Symbol(params.get("var", "x"))
    for idx, step in enumerate(rubric):
        if step["kind"] == "simple":
            for j, (i, text) in enumerate(parts):
                if not part_used[j] and step_matches(text, step["value"], tolerance or 1e-4, step.get("constant_ok", False),
                                                     var_sym, step.get("angle", False), step.get("alternatives"),
                                                     step.get("free_constants")):
                    matched_line_idx[idx] = i
                    part_used[j] = True
                    break
        else:
            # A structured final answer is judged on a whole line, which it
            # then claims entirely.
            for i, raw in enumerate(work):
                line_parts = [j for j, (k, _) in enumerate(parts) if k == i]
                if any(part_used[j] for j in line_parts):
                    continue
                if _judged_step_matches(topic, question_type, params, step, raw, tolerance):
                    matched_line_idx[idx] = i
                    for j in line_parts:
                        part_used[j] = True
                    break

    as_term = set()
    if term_credit:
        item_answer = {step["item"]: step["value"] for step in rubric}  # the item's last step
        given = solve(topic, question_type, params).get("given")
        for idx, step in enumerate(rubric):
            if matched_line_idx[idx] is not None or step["kind"] != "simple" or step.get("subject") is None:
                continue
            coeff = _term_coefficient(given, step["subject"])
            if coeff is None:
                continue
            for i, text in parts:
                if _shown_as_term(text, coeff * step["value"], item_answer[step["item"]]):
                    matched_line_idx[idx] = i
                    as_term.add(idx)
                    break

    via_prime = set()
    if prime_credit:
        for i, raw in enumerate(work):
            for value in _prime_shown_values(raw, [s["value"] for s in rubric if s["kind"] == "simple"], var_sym):
                for idx, step in enumerate(rubric):
                    if matched_line_idx[idx] is None and step["kind"] == "simple" \
                            and not isinstance(step["value"], (list, tuple)) and _same_term(value, step["value"]):
                        matched_line_idx[idx] = i
                        via_prime.add(idx)
                        break

    implied = set()
    if implied_credit:
        item_step_indices = {}
        for idx, step in enumerate(rubric):
            item_step_indices.setdefault(step["item"], []).append(idx)
        solution_given = solve(topic, question_type, params).get("given")
        for idxs in item_step_indices.values():
            last = rubric[idxs[-1]]
            if not _shows_work(work, [last["value"], *(last.get("alternatives") or [])], solution_given,
                               var_sym, last.get("angle", False)):
                continue
            last_matched_pos = max(
                (pos for pos, idx in enumerate(idxs) if matched_line_idx[idx] is not None),
                default=None,
            )
            if last_matched_pos is not None:
                for pos in range(last_matched_pos):
                    if matched_line_idx[idxs[pos]] is None:
                        implied.add(idxs[pos])

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
        if idx in as_term:
            entry["as_term"] = True
        if idx in via_prime:
            entry["via_prime"] = True
        breakdown.append(entry)
    return {"earned": earned, "possible": possible, "breakdown": breakdown}


def default_score_work(topic, question_type, params, lines, question_points=DEFAULT_QUESTION_POINTS,
                       tolerance=None, part_label=None):
    """The default scoring policy (implied credit, a line read by its last
    value) — what a topic's ``rubric.py`` uses unless it has its own rules.
    `part_label`: see `build_rubric`."""
    rubric = build_rubric(topic, question_type, params, question_points, part_label)
    return score_rubric(topic, question_type, params, rubric, lines, tolerance)


def method_rubric(**policy):
    """(score_work, select_method) for a topic whose blueprints may hold
    several methods (alternative solution paths, ``engine/core/blueprints.py``):
    the work is scored with `score_rubric(**policy)` against the method it
    follows, and ``grading.analyze_work`` marks the lines against that same
    method (via the topic's ``select_method``), so the marks and the points
    always agree. Each breakdown entry also carries the step's value with
    this question's numbers (``expected``/``expected_latex``), so a missed
    step can be shown to the student."""
    import json
    from functools import lru_cache

    from sympy import latex

    def _score(topic, question_type, params, lines, question_points, tolerance, part_label, method):
        rubric = build_rubric(topic, question_type, params, question_points, part_label, method)
        result = score_rubric(topic, question_type, params, rubric, lines, tolerance, **policy)
        for step, entry in zip(rubric, result["breakdown"]):
            if step.get("label_latex"):
                entry["label_latex"] = step["label_latex"]
            entry["expected"] = str(step["value"])
            entry["expected_latex"] = latex(step["value"])
        return result

    @lru_cache(maxsize=256)
    def _select_cached(key):
        topic, question_type, params_json, lines, question_points, tolerance, part_label = key
        params = json.loads(params_json)
        methods = solve(topic, question_type, params).get("methods") or []
        if len(methods) < 2:
            return None
        return pick_method(methods, lambda m: _score(topic, question_type, params, list(lines),
                                                      question_points, tolerance, part_label, m))

    def select_method(topic, question_type, params, lines, question_points=DEFAULT_QUESTION_POINTS,
                      tolerance=None, part_label=None):
        """The blueprint method the work follows (None with fewer than two)."""
        return _select_cached((topic, question_type, json.dumps(params, sort_keys=True, default=str),
                               tuple(lines), question_points, tolerance, part_label))

    def score_work(topic, question_type, params, lines, question_points=DEFAULT_QUESTION_POINTS,
                   tolerance=None, part_label=None):
        """Score the work against the method it follows, reported as "method"."""
        method = select_method(topic, question_type, params, lines, question_points, tolerance, part_label)
        result = _score(topic, question_type, params, lines, question_points, tolerance, part_label, method)
        if method:
            result["method"] = method
        return result

    return score_work, select_method


def pick_method(methods, score):
    """The blueprint method (id) a student's work follows: highest score,
    then most steps actually written (methods with fewer, heavier steps can
    tie on points); ties -> the earlier, i.e. standard, method. `score(id)`
    returns a `score_rubric` result."""
    best, best_key = None, None
    for m in methods:
        result = score(m["method"])
        written = sum(1 for b in result["breakdown"] if b["matched_line"] is not None)
        key = (result["earned"], written)
        if best_key is None or key > best_key:
            best, best_key = m["method"], key
    return best


def _shows_work(work, final_values, given, var_sym, angle=False):
    """True when some line is an actual derivation step rather than just the
    final answer or the given restated: a chained computation ('a = ... = ...')
    or an equation whose value is neither the final answer nor the given.
    A letters-only value ('(a+b)^2 = a^2 + 2ab + b^2') is a formula copied
    down, not work, unless it involves the problem's own variable."""
    for raw in work:
        text = _strip_khmer(raw)
        if "=" not in text:
            continue
        if text.count("=") >= 2:
            return True
        try:
            value = parse_answer(_value_str(text))
        except Exception:
            continue
        syms = getattr(value, "free_symbols", set())
        if syms and var_sym not in syms:
            continue
        finals = [v for v in final_values if is_simple_value(v) and not isinstance(v, (list, tuple))]
        # A line opening with "=" continues the previous line's chain — OCR
        # puts each "= ..." of a multi-line derivation on its own line, so the
        # count("=") rule above never sees the chain. Such a line is work even
        # when it's an algebraic rewrite equal to the given (dividing top and
        # bottom by x), as long as it isn't the given copied verbatim or the
        # final answer itself.
        if text.lstrip().startswith("="):
            try:
                verbatim_given = given is not None and value == given
            except Exception:
                verbatim_given = False
            if not verbatim_given and not any(_scalar_matches(value, v, 1e-9) for v in finals):
                return True
        others = finals + ([given] if given is not None and is_simple_value(given) else [])
        if any(_scalar_matches(value, v, 1e-9) for v in others):
            continue
        if angle and any(_angle_close(value, v, 1e-9) for v in finals):
            continue
        return True
    return False


def _term_coefficient(given, subject):
    """c when the given is a sum with the term c*subject (c a nonzero
    number), else None."""
    try:
        terms = Add.make_args(sympify(given))
        subject = sympify(subject)
    except Exception:
        return None
    if len(terms) < 2:
        return None
    for t in terms:
        try:
            c = simplify(t / subject)
        except Exception:
            continue
        if c.is_number and c != 0:
            return c
    return None


def _shown_as_term(text, value, answer):
    """True when `value` is written as a term of a sum on this line that is
    also a term of the correct `answer` (so a sign error never shows a
    step), e.g. -2*exp(-2*x) in ``4 - 2*exp(-2*x)``. A line that IS the
    value is left to `step_matches`."""
    try:
        got = parse_answer(_value_str(text))
        right = Add.make_args(sympify(answer))
    except Exception:
        return False
    if not isinstance(got, Add):
        return False
    return any(_same_term(h, value) and any(_same_term(h, r) for r in right)
               for h in Add.make_args(got))


def _same_term(a, b):
    try:
        return a == b or simplify(a - b) == 0
    except Exception:
        return False


def _prime_shown_values(raw, correct_values, var_sym):
    """Values a line shows through ``(E)'`` slots (see `prime_credit` in
    `score_rubric`): the factor multiplying each slot, and the value the next
    "=" part substitutes for it — only from a part that is correct with every
    slot set to the true derivative."""
    text = _strip_khmer(raw)
    chain = [c.strip() for c in text.split("=")]
    shown = []
    for p, part in enumerate(chain):
        slots = prime_slots(part)
        if not slots:
            continue
        try:
            derivs = [diff(parse_answer(inner), var_sym) for _, _, inner in slots]
            true_value = parse_answer(fill_prime_slots(part, slots, derivs))
        except Exception:
            continue
        if not any(_same_term(true_value, v) for v in correct_values if not isinstance(v, (list, tuple))):
            continue
        nxt = None
        if p + 1 < len(chain) and chain[p + 1] and not prime_slots(chain[p + 1]):
            try:
                nxt = parse_answer(chain[p + 1])
            except Exception:
                nxt = None
        if nxt is not None and _same_term(nxt, true_value):
            # The rule written out, then substituted correctly: a quotient's
            # numerator (u'v - uv') is shown by that substituted fraction.
            num, den = fraction(nxt)
            if den != 1:
                shown.append(num)
        for s in range(len(slots)):
            try:
                one = parse_answer(fill_prime_slots(part, slots, [1 if t == s else d for t, d in enumerate(derivs)]))
                zero = parse_answer(fill_prime_slots(part, slots, [0 if t == s else d for t, d in enumerate(derivs)]))
                factor = simplify(one - zero)
            except Exception:
                continue
            if factor == 0:
                continue
            shown.append(factor)
            if nxt is not None:
                used = simplify((nxt - zero) / factor)
                if _same_term(used, derivs[s]):
                    shown.append(used)
    return shown


def _judged_step_matches(topic, question_type, params, step, line, tolerance):
    try:
        if step["item"] != question_type:
            verdict = grade_part(topic, question_type, params, step["item"], line, tolerance)
        else:
            verdict = grade(topic, question_type, params, line, tolerance)
    except Exception:
        return False
    return bool(verdict.get("correct"))
