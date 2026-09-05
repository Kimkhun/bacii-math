"""Function-study solvers: multi-part BAC II exercises built from one function
g(x) — domain, parity, one-sided limits, tangent line, derivative of a product,
and an area integral. SymPy computes every answer; the curated exercise card
(backend/data/functions/*.json) supplies the MoEYS narration text. Assembly
mirrors solver/probability.py's multi-part pattern (work_mode "any_order",
part-labeled steps and checkpoints, target = last part)."""
from sympy import N, Symbol, diff, div, integrate, latex, limit, log, logcombine, oo, simplify, solve, sympify

from .functions_display import (
    render_answer,
    render_question,
    render_steps,
)
from .shared import _calc_locals, _formula_tags, inline_latex


def _f(v):
    """SymPy number -> float (∞ -> inf, -∞ -> -inf)."""
    if v == oo:
        return float("inf")
    if v == -oo:
        return float("-inf")
    return float(N(v, 8))


def _shape_of(expr):
    """Function shape for step-narrative selection: 'log' (contains ln of a
    quotient), 'exp' (contains an exponential), else 'rational'."""
    if expr.has(log):
        return "log"
    if expr.has(log, Symbol("exp")) or any(str(a.func) in ("exp", "ExpBase") for a in expr.atoms()):
        return "exp"
    return "rational"


def _log_split(expr, x):
    """For g(x)=ln(P/Q), return (P, Q): numerator and denominator of the log
    argument (so the split form is ln(P) - ln(Q))."""
    arg = expr.args[0] if isinstance(expr, log) else expr
    P, Q = arg.as_numer_denom()
    return simplify(P), simplify(Q)


def _strip_float(v):
    if v == int(v):
        return str(int(v))
    return f"{v:g}"


def _interval_display(ivs):
    def iv(iv):
        lo = "-∞" if iv["lo"] == float("-inf") else _strip_float(iv["lo"])
        hi = "∞" if iv["hi"] == float("inf") else _strip_float(iv["hi"])
        return f"({lo}, {hi})"

    return " ∪ ".join(iv(i) for i in ivs)


def _positive_intervals(u, x):
    """Open intervals where the real expression u > 0, by sign-testing between
    the roots of its numerator and denominator (the MoEYS sign-table method)."""
    num, den = u.as_numer_denom()
    pts = set(r for r in solve(num, x) if r.is_real)
    pts.update(r for r in solve(den, x) if r.is_real)
    pts = sorted(pts)
    if not pts:
        bounds = [(-oo, oo)]
    else:
        bounds = [(-oo, pts[0])]
        bounds += [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        bounds.append((pts[-1], oo))
    out = []
    for lo, hi in bounds:
        if lo == -oo and hi == oo:
            mid = 0
        elif hi == oo:
            mid = lo + 1
        elif lo == -oo:
            mid = hi - 1
        else:
            mid = (lo + hi) / 2
        val = simplify(u.subs(x, mid))
        positive = val.is_positive if val.is_positive is not None else N(val) > 0
        if positive:
            out.append({"lo": _f(lo), "hi": _f(hi), "lo_open": True, "hi_open": True})
    return out


def _sign_rows(u, x):
    """Sign-table rows for the MoEYS method.
    Alternates: [region 0, root 0, region 1, root 1, ..., region N] (2*N + 1 items).
    Returns {cols, rows}."""
    num, den = u.as_numer_denom()
    roots = sorted(set(r for r in solve(num, x) if r.is_real) | set(r for r in solve(den, x) if r.is_real))
    num_roots = [r for r in solve(num, x) if r.is_real]
    den_roots = [r for r in solve(den, x) if r.is_real]

    def region_sign(factor, i):
        lo = float("-inf") if i == 0 else float(_f(roots[i - 1]))
        hi = float("inf") if i == len(roots) else float(_f(roots[i]))
        mid = 0 if (lo == float("-inf") and hi == float("inf")) else (
            lo + 1 if hi == float("inf") else (
                hi - 1 if lo == float("-inf") else (lo + hi) / 2))
        v = simplify(factor.subs(x, mid))
        return "+" if (v.is_positive or (v.is_positive is None and float(N(v)) > 0)) else "-"

    nregions = len(roots) + 1

    def factor_cells(factor, own_roots):
        cells = []
        for i in range(len(roots)):
            cells.append(region_sign(factor, i))
            r = roots[i]
            if any(abs(float(oroot) - float(r)) < 1e-9 for oroot in own_roots):
                cells.append("0")
            else:
                cells.append("|")
        cells.append(region_sign(factor, len(roots)))
        return cells

    row_num = factor_cells(num, num_roots)
    row_den = factor_cells(den, den_roots)

    # quotient row: combine signs, 0 at num roots, ‖ at den roots
    qrow = []
    for i in range(len(roots)):
        s_num = row_num[2 * i]
        s_den = row_den[2 * i]
        qrow.append("+" if s_num == s_den else "-")
        r = roots[i]
        is_den = any(abs(float(oroot) - float(r)) < 1e-9 for oroot in den_roots)
        is_num = any(abs(float(oroot) - float(r)) < 1e-9 for oroot in num_roots)
        if is_den:
            qrow.append("‖")
        elif is_num:
            qrow.append("0")
        else:
            qrow.append("|")
    s_num_last = row_num[-1]
    s_den_last = row_den[-1]
    qrow.append("+" if s_num_last == s_den_last else "-")

    col_labels = ["−∞"] + [_strip_float(_f(r)) for r in roots] + ["+∞"]
    return {
        "cols": col_labels,
        "rows": [
            {"label": latex(num), "cols": [{"val": v} for v in row_num]},
            {"label": latex(den), "cols": [{"val": v} for v in row_den]},
            {"label": latex(num / den), "cols": [{"val": v} for v in qrow]},
        ],
    }


def _near_sign(expr, x, point, side):
    """Sign (+1/-1) of the one-sided limit value at a finite point, inferred by
    evaluating just to that side (used to write 0^+ / 0^-)."""
    eps = 1e-6
    xp = point - eps if side == "-" else point + eps
    try:
        val = float(N(limit(expr, x, point, dir=side), 4))
    except Exception:
        val = float(N(expr.subs(x, xp), 4))
    if abs(val) < 1e-9:
        # both sides tiny: pick sign from the expression's sign just off point
        val = float(N(expr.subs(x, xp), 4))
    return 1 if val > 0 else -1


def _behavior_string(P, Q, point, side, x, pl, ql):
    """LaTeX string for the argument's behavior at a one-sided limit, e.g.
    '\\frac{0^{+}}{-6}' for ln(P/Q) near a boundary."""
    def part_str(val, expr):
        if val == 0:
            return f"0^{{+}}" if _near_sign(expr, x, point, side) > 0 else f"0^{{-}}"
        if val in (oo, -oo):
            return "+\\infty" if val == oo else "-\\infty"
        return latex(val)
    return f"\\frac{{{part_str(pl, P)}}}{{{part_str(ql, Q)}}}"


def _part_solution(part, answer_exact, answer_latex, answer_display, answer_decimal, steps, checkpoints, ctx=None):
    res = {
        "label": part["label"],
        "want": part.get("want"),
        "answer_kind": part.get("kind", "expression"),
        "answer_exact": answer_exact,
        "answer_latex": answer_latex,
        "answer_display": answer_display,
        "answer_decimal": answer_decimal,
        "steps": steps,
        "checkpoints": checkpoints,
        "formula_tags": _formula_tags(steps),
        "choices": part.get("choices"),
        "technique": part.get("technique", ""),
        "exact_only": part.get("exact_only", False),
        "_ctx": ctx or {},
    }
    if ctx and "sign_rows" in ctx:
        res["sign_table"] = ctx["sign_rows"]
    return res


def _solve_part_domain(params, x, expr, part):
    if isinstance(expr, log):
        u = expr.args[0] if isinstance(expr, log) else expr
        ivs = _positive_intervals(u, x)
        display = part.get("display") or _interval_display(ivs)
        num, den = u.as_numer_denom()
        boundaries = sorted(set(_f(r) for r in (solve(num, x) + solve(den, x)) if r.is_real))
        steps = [
            {"title": "Domain of a logarithm",
             "detail": f"\\(\\ln(u)\\) is defined only when \\(u > 0\\), with \\(u = {inline_latex(u)}\\).",
             "formula": "domain_log"},
            {"title": "Locate the boundary points",
             "detail": f"Numerator \\(u=0\\) at \\({', '.join(str(b) for b in boundaries)}\\) — build the sign table of \\(u\\).",
             "formula": "sign_table"},
            {"title": "Read the sign table", "detail": part.get("technique", ""), "formula": "sign_table"},
            {"title": "Conclusion", "detail": f"The domain is \\(D = {display}\\).", "formula": "sign_table"},
        ]
        checkpoints = [{"label": "domain", "value": ivs, "formula": "sign_table"}]
        checkpoints += [{"label": f"boundary {b}", "value": b, "formula": "sign_table"} for b in boundaries]
        P, Q = _log_split(expr, x)
        num, den = u.as_numer_denom()
        roots = sorted(set(_f(r) for r in (solve(num, x) + solve(den, x)) if r.is_real))
        col_labels = ["−∞"] + [_strip_float(r) for r in roots] + ["+∞"]
        return _part_solution(part, ivs, display, display, None, steps, checkpoints,
                              ctx={"interval": _interval_display(ivs), "boundaries": boundaries,
                                   "shape": "log", "num": latex(num), "den": latex(den),
                                   "col_labels": col_labels,
                                   "P": latex(P), "Q": latex(Q),
                                   "P_eq_zero": [latex(r) for r in solve(num, x) if r.is_real],
                                   "Q_eq_zero": [latex(r) for r in solve(den, x) if r.is_real],
                                   "sign_rows": _sign_rows(u, x)})

    num, den = expr.as_numer_denom()
    poles = sorted(set(_f(r) for r in solve(den, x) if r.is_real))
    if not poles:
        ivs = [{"lo": float("-inf"), "hi": float("inf"), "lo_open": True, "hi_open": True}]
    else:
        bounds = [float("-inf")] + poles + [float("inf")]
        ivs = [{"lo": bounds[i], "hi": bounds[i + 1], "lo_open": True, "hi_open": True}
               for i in range(len(bounds) - 1)]
    display = part.get("display") or _interval_display(ivs)
    steps = [
        {"title": "Domain of a rational function",
         "detail": f"\\(f(x) = {inline_latex(expr)}\\) is defined wherever the denominator is non-zero.",
         "formula": "rational_domain"},
        {"title": "Denominator roots",
         "detail": f"The denominator \\({inline_latex(den)}\\) vanishes at \\({', '.join(str(b) for b in poles) or 'no real point'}\\).",
         "formula": "rational_domain"},
        {"title": "Conclusion", "detail": f"The domain is \\(D = {display}\\).", "formula": "rational_domain"},
    ]
    checkpoints = [{"label": "domain", "value": ivs, "formula": "rational_domain"}]
    checkpoints += [{"label": f"pole {b}", "value": b, "formula": "rational_domain"} for b in poles]
    return _part_solution(part, ivs, display, display, None, steps, checkpoints,
                          ctx={"interval": display, "boundaries": poles})


def _solve_part_parity(params, x, expr, part):
    gm = expr.subs(x, -x)
    odd = simplify(logcombine(gm + expr, force=True)) == 0
    even = simplify(logcombine(gm - expr, force=True)) == 0
    verdict = "odd" if odd else "even" if even else "neither"
    display = part.get("display") or verdict
    steps = [
        {"title": "Compute g(-x)",
         "detail": f"\\(g(-x) = {latex(gm)}\\).", "formula": "log_quotient_rule"},
        {"title": "Rewrite using log rules", "detail": part.get("technique", ""), "formula": "log_reciprocal"},
        {"title": "Conclusion",
         "detail": f"\\(g(-x) + g(x) = 0\\), i.e. \\(g(-x) = -g(x)\\), so \\(g\\) is {verdict}.",
         "formula": "parity_definition"},
    ]
    checkpoints = [{"label": "g(-x) + g(x)", "value": 0, "formula": "parity_definition"}]
    P, Q = _log_split(expr, x)
    ctx = {"verdict": verdict, "shape": "log", "split": f"{latex(expr)} = {latex(log(P))} - {latex(log(Q))}",
           "P": latex(P), "Q": latex(Q), "gminusx": latex(gm)}
    return _part_solution(part, verdict, display, display, None, steps, checkpoints, ctx=ctx)


def _solve_part_limit(params, x, expr, part):
    var = params["var"]
    point = sympify(part["point"], locals=_calc_locals(var))
    side = part.get("side")
    result = limit(expr, x, point, dir=side) if side else limit(expr, x, point)
    point_latex = latex(point) + ("^+" if side == "+" else "^-" if side == "-" else "")
    display = part.get("display") or (latex(result) if result in (oo, -oo) else str(result))

    fn_name = params.get("fn_name", "g")
    res_latex = "+\\infty" if result == oo else ("-\\infty" if result == -oo else latex(result))

    if isinstance(expr, log):
        P, Q = _log_split(expr, x)
        pl = limit(P, x, point, dir=side) if side else limit(P, x, point)
        ql = limit(Q, x, point, dir=side) if side else limit(Q, x, point)
        bs = _behavior_string(P, Q, point, side, x, pl, ql)
        behavior = bs
        chain = f"\\lim_{{{var} \\to {point_latex}}} {fn_name}({var}) = \\lim_{{{var} \\to {point_latex}}} \\ln\\left(\\frac{{{latex(P)}}}{{{latex(Q)}}}\\right) = \\ln\\left({bs}\\right) = {res_latex}"
    else:
        num, den = expr.as_numer_denom()
        pl = limit(num, x, point, dir=side) if side else limit(num, x, point)
        ql = limit(den, x, point, dir=side) if side else limit(den, x, point)
        behavior = None
        if ql == 0:
            q_sign = "0^{+}" if _near_sign(den, x, point, side) > 0 else "0^{-}"
            chain = f"\\lim_{{{var} \\to {point_latex}}} {fn_name}({var}) = \\lim_{{{var} \\to {point_latex}}} \\frac{{{latex(num)}}}{{{latex(den)}}} = \\frac{{{latex(pl)}}}{{{q_sign}}} = {res_latex}"
        else:
            chain = f"\\lim_{{{var} \\to {point_latex}}} {fn_name}({var}) = \\lim_{{{var} \\to {point_latex}}} \\frac{{{latex(num)}}}{{{latex(den)}}} = {res_latex}"

    steps = [
        {"title": f"Limit at {point_latex}",
         "detail": chain,
         "formula": "vertical_asymptote"},
    ]
    checkpoints = [{"label": "limit", "value": result, "formula": "vertical_asymptote"}]
    decimal = None if result in (oo, -oo) else _f(result)
    ctx = {
        "point": str(point),
        "side": side,
        "value": str(result),
        "value_latex": res_latex,
        "infinite": result in (oo, -oo),
        "shape": "log" if isinstance(expr, log) else "rational",
        "arg": latex(expr.args[0]) if isinstance(expr, log) else latex(expr),
        "fn": fn_name,
        "behavior": behavior,
        "chain": chain,
    }
    return _part_solution(part, result, latex(result), display, decimal, steps, checkpoints, ctx=ctx)


def _solve_part_limits(params, x, expr, part):
    """Compute a batch of one-sided / infinite limits as one part (e.g. the
    original exam item "compute the limits at 2 and at ±∞"). The answer is the
    last listed limit; every limit is a checkpoint so any_order line-matching
    credits each one."""
    var = params["var"]
    results = []
    for it in part.get("items") or []:
        point = sympify(it["point"], locals=_calc_locals(var))
        side = it.get("side")
        r = limit(expr, x, point, dir=side) if side else limit(expr, x, point)
        pl = latex(point) + ("^+" if side == "+" else "^-" if side == "-" else "")
        results.append({"point": pl, "value": r})
    answer = results[-1]["value"] if results else None
    summary = "; ".join(f"\\lim_{{{var} \\to {r['point']}}} = {latex(r['value'])}" for r in results)
    display = part.get("display") or "; ".join(str(r["value"]) for r in results)
    steps = [
        {"title": "Compute the limits",
         "detail": f"f({var}) = {latex(expr)}",
         "formula": "setup_limit"},
        {"title": "Evaluate each",
         "detail": summary,
         "formula": "vertical_asymptote"},
        {"title": "Conclusion",
         "detail": summary,
         "formula": "vertical_asymptote"},
    ]
    checkpoints = [
        {"label": f"lim {var}->{r['point']}", "value": r["value"], "formula": "vertical_asymptote"}
        for r in results
    ]
    decimal = None if answer in (oo, -oo) else _f(answer)
    ctx = {"results": [{"point": r["point"], "value": latex(r["value"])} for r in results]}
    return _part_solution(part, answer, latex(answer), display, decimal, steps, checkpoints, ctx=ctx)


def _solve_part_draw(params, x, expr, part):
    """The "draw the graph" item: no numeric answer to grade — the frontend runs
    the graph-drawing check (gradeGraph) against this part's canvas instead. The
    trivial solution keeps the exercise persistable/gradable end to end."""
    display = part.get("display") or "draw the graph"
    steps = [
        {"title": "Draw the graph",
         "detail": part.get("technique",
                            "Sketch the curve (C) together with its asymptotes and any tangents."),
         "formula": "graph_drawing"},
    ]
    checkpoints = [{"label": "graph drawn", "value": "graph", "formula": "graph_drawing"}]
    return _part_solution(part, "graph", "\\text{graph}", display, None, steps, checkpoints)


def _solve_part_variation(params, x, expr, part):
    """Variation table item (when it's its own exam part): the derivative, its
    critical points, and the extremum values. The part answer is the value of f
    at the critical point indexed by ``part["idx"]`` (default 0); the critical
    points and extremum values are checkpoints for line-level credit."""
    var = params["var"]
    der = simplify(diff(expr, x))
    crit = sorted(set(r for r in solve(der, x) if r.is_real))
    idx = int(part.get("idx", 0))
    answer = None
    checkpoints = [{"label": "f'(x)", "value": der, "formula": "quotient_rule"}]
    for i, c in enumerate(crit):
        v = simplify(expr.subs(x, c))
        checkpoints.append({"label": f"critical {c}", "value": c, "formula": "monotonicity_sign"})
        checkpoints.append({"label": f"f({c})", "value": v, "formula": "monotonicity_sign"})
        if i == idx:
            answer = v
    display = part.get("display") or ("variation table" if answer is None else f"extremum f = {latex(answer)}")
    steps = [
        {"title": "Derivative",
         "detail": f"\\(f'({var}) = {inline_latex(der)}\\).",
         "formula": "quotient_rule"},
        {"title": "Critical points",
         "detail": part.get("technique", "") or f"\\(f'({var}) = 0\\) at \\({', '.join(str(c) for c in crit) or 'no real point'}\\).",
         "formula": "monotonicity_sign"},
        {"title": "Extrema",
         "detail": f"The extremum values are \\({'; '.join(f'f({latex(c)}) = {latex(simplify(expr.subs(x, c)))}' for c in crit) or 'none'}\\).",
         "formula": "monotonicity_sign"},
    ]
    return _part_solution(part, answer, latex(answer), display, None, steps, checkpoints,
                          ctx={"der": latex(der)})


def _solve_part_derivative(params, x, expr, part):
    var = params["var"]
    der = simplify(diff(expr, x))
    display = part.get("display") or latex(der)
    steps = [
        {"title": "Differentiate",
         "detail": f"Differentiate \\(f(x) = {inline_latex(expr)}\\).",
         "formula": "quotient_rule"},
        {"title": "Simplify",
         "detail": part.get("technique", "") or "Collect the terms over a common denominator.",
         "formula": "quotient_rule"},
        {"title": "Result", "detail": f"\\(f'(x) = {inline_latex(der)}\\).", "formula": "quotient_rule"},
    ]
    checkpoints = [{"label": "f'(x)", "value": der, "formula": "quotient_rule"}]
    P, Q = _log_split(expr, x)
    ctx = {"expr": latex(der), "shape": "log",
           "split": f"{latex(expr)} = {latex(log(P))} - {latex(log(Q))}",
           "P": latex(P), "Q": latex(Q),
           "dP": latex(diff(P, x)), "dQ": latex(diff(Q, x))}
    return _part_solution(part, der, latex(der), display, None, steps, checkpoints, ctx=ctx)


def _solve_part_asymptote(params, x, expr, part):
    var = params["var"]
    inf = oo if part.get("side", "+") == "+" else -oo
    m = limit(expr / x, x, inf)
    b = simplify(limit(expr - m * x, x, inf))
    if m == 0:
        line, kind = simplify(b), "horizontal"
    else:
        line, kind = simplify(m * x + b), "oblique"
    display = part.get("display") or f"y = {latex(line)}"
    steps = [
        {"title": f"Find the {kind} asymptote",
         "detail": f"\\(\\lim_{{{var}\\to \\infty}} f({var})/{var} = {inline_latex(m)}\\), giving the slope.",
         "formula": "oblique_asymptote"},
        {"title": "Intercept",
         "detail": f"\\(\\lim_{{{var}\\to \\infty}} \\big(f({var}) - {inline_latex(m)}{var}\\big) = {inline_latex(b)}\\).",
         "formula": "oblique_asymptote"},
        {"title": "Conclusion",
         "detail": f"The {kind} asymptote is \\(y = {inline_latex(line)}\\).", "formula": "oblique_asymptote"},
    ]
    checkpoints = [{"label": "asymptote", "value": line, "formula": "oblique_asymptote"}]
    ctx = {"line": latex(line), "kind": kind}
    return _part_solution(part, line, latex(line), display, None, steps, checkpoints, ctx=ctx)


def _solve_part_decompose(params, x, expr, part):
    var = params["var"]
    num, den = expr.as_numer_denom()
    q, r = div(num, den, x)
    dec = simplify(q + r / den)
    a = simplify(diff(q, x))
    b = simplify(q - a * x)
    c = simplify(r)
    display = part.get("display") or f"f(x) = {latex(dec)}"
    steps = [
        {"title": "Polynomial division",
         "detail": f"\\frac{{{latex(num)}}}{{{latex(den)}}}",
         "formula": "euclidean_division"},
        {"title": "Quotient and remainder",
         "detail": f"q(x) = {latex(q)},\\ r = {latex(r)} \\implies f(x) = {latex(dec)}",
         "formula": "euclidean_division"},
        {"title": "Identify a, b, c",
         "detail": f"a = {latex(a)},\\ b = {latex(b)},\\ c = {latex(c)}",
         "formula": "euclidean_division"},
    ]
    checkpoints = [
        {"label": "decomposition", "value": dec, "formula": "euclidean_division"},
        {"label": "a", "value": a, "formula": "euclidean_division"},
        {"label": "b", "value": b, "formula": "euclidean_division"},
        {"label": "c", "value": c, "formula": "euclidean_division"},
    ]
    ctx = {"dec": latex(dec), "a": latex(a), "b": latex(b), "c": latex(c)}
    return _part_solution(part, dec, latex(dec), display, None, steps, checkpoints, ctx=ctx)


def _solve_part_position(params, x, expr, part):
    var = params["var"]
    line = sympify(part["line_expr"], locals=_calc_locals(var))
    diff_expr = simplify(expr - line)
    ivs = _positive_intervals(diff_expr, x)
    display = part.get("display") or _interval_display(ivs)
    steps = [
        {"title": "Difference with the line",
         "detail": f"\\(f(x) - y = {inline_latex(diff_expr)}\\).",
         "formula": "position_asymptote"},
        {"title": "Sign of the difference",
         "detail": part.get("technique", ""), "formula": "position_asymptote"},
        {"title": "Conclusion",
         "detail": f"\\(C\\) lies above \\(d\\) when the difference is positive, i.e. on \\({display}\\).",
         "formula": "position_asymptote"},
    ]
    checkpoints = [{"label": "above line", "value": ivs, "formula": "position_asymptote"}]
    below = _positive_intervals(simplify(-diff_expr), x)
    ctx = {"above": _interval_display(ivs), "below": _interval_display(below)}
    return _part_solution(part, ivs, display, display, None, steps, checkpoints, ctx=ctx)


def _solve_part_symmetry(params, x, expr, part):
    var = params["var"]
    a0 = sympify(part["x0"], locals=_calc_locals(var))
    b0 = sympify(part["y0"], locals=_calc_locals(var))
    t = Symbol("t")
    s = simplify(expr.subs(x, a0 + t) + expr.subs(x, a0 - t))
    target = simplify(2 * b0)
    center = simplify(s - target) == 0
    display = part.get("display") or ("center of symmetry" if center else "not a center")
    steps = [
        {"title": "Translate to the candidate center",
         "detail": f"Compute \\(f({inline_latex(a0)}+t) + f({inline_latex(a0)}-t)\\).",
         "formula": "center_symmetry"},
        {"title": "Evaluate",
         "detail": f"\\(f({inline_latex(a0)}+t) + f({inline_latex(a0)}-t) = {inline_latex(s)} = 2\\times {inline_latex(b0)}\\).",
         "formula": "center_symmetry"},
        {"title": "Conclusion",
         "detail": ("Hence I is the center of symmetry of C." if center
                    else "Hence I is not the center of symmetry."),
         "formula": "center_symmetry"},
    ]
    checkpoints = [{"label": "f(a+t)+f(a-t)", "value": target, "formula": "center_symmetry"}]
    ctx = {"center": center, "a0": latex(a0), "b0": latex(b0)}
    return _part_solution(part, target, latex(target), display, None, steps, checkpoints, ctx=ctx)


def _solve_part_tangent(params, x, expr, part):
    var = params["var"]
    x0 = sympify(part["x0"], locals=_calc_locals(var))
    y0 = simplify(expr.subs(x, x0))
    m = simplify(diff(expr, x).subs(x, x0))
    line = simplify(m * (x - x0) + y0)
    display = part.get("display") or f"y = {latex(line)}"
    steps = [
        {"title": "Point of tangency",
         "detail": f"\\(g({latex(x0)}) = {inline_latex(y0)}\\).", "formula": "derivative_ln"},
        {"title": "Slope of the tangent",
         "detail": f"\\(g'({latex(x0)}) = {inline_latex(m)}\\).", "formula": "derivative_ln"},
        {"title": "Equation of the tangent",
         "detail": f"\\(T: y - {inline_latex(y0)} = {inline_latex(m)}(x - {latex(x0)})\\), i.e. \\({inline_latex(line)}\\).",
         "formula": "tangent_equation"},
    ]
    checkpoints = [
        {"label": f"g({latex(x0)})", "value": y0, "formula": "derivative_ln"},
        {"label": f"g'({latex(x0)})", "value": m, "formula": "derivative_ln"},
        {"label": "tangent line", "value": line, "formula": "tangent_equation"},
    ]
    ctx = {"x0": latex(x0), "y0": latex(y0), "m": latex(m), "line": latex(line),
           "shape": "log", "x0_num": str(x0), "y0_num": str(y0), "m_num": str(m),
           "x0_plain": latex(x0)}
    return _part_solution(part, line, latex(line), display, None, steps, checkpoints, ctx=ctx)


def _solve_part_derivative_product(params, x, expr, part):
    var = params["var"]
    h = sympify(part["h_expr"], locals=_calc_locals(var))
    der = simplify(diff(h, x))
    display = part.get("display") or latex(der)
    steps = [
        {"title": "Apply the product rule",
         "detail": f"\\(h(x) = x\\,g(x)\\), so \\(h'(x) = g(x) + x\\,g'(x)\\).",
         "formula": "product_rule"},
        {"title": "Substitute g and g'", "detail": part.get("technique", ""), "formula": "derivative_ln"},
        {"title": "Result", "detail": f"\\(h'(x) = {inline_latex(der)}\\).", "formula": "product_rule"},
    ]
    checkpoints = [{"label": "h'(x)", "value": der, "formula": "product_rule"}]
    P, Q = _log_split(expr, x)
    gprime = simplify(diff(expr, x))
    ctx = {"h_fn": part.get("h_fn", "h"), "expr": latex(der), "shape": "log",
           "split": f"{latex(expr)} = {latex(log(P))} - {latex(log(Q))}",
           "P": latex(P), "Q": latex(Q), "g": latex(expr), "gprime": latex(gprime)}
    return _part_solution(part, der, latex(der), display, None, steps, checkpoints, ctx=ctx)


def _solve_part_integral(params, x, expr, part):
    var = params["var"]
    lower = sympify(part["lower"], locals=_calc_locals(var))
    upper = sympify(part["upper"], locals=_calc_locals(var))
    result = integrate(expr, (x, lower, upper))
    display = part.get("display") or latex(result)
    h = sympify(f"{var}*({params['function_expr']})", locals=_calc_locals(var))
    h_upper = simplify(h.subs(x, upper))
    h_lower = simplify(h.subs(x, lower))
    steps = [
        {"title": "Rewrite the integrand",
         "detail": part.get("technique", ""), "formula": "antiderivative_reciprocal_ln"},
        {"title": "Integrate",
         "detail": f"\\(\\int_{{{latex(lower)}}}^{{{latex(upper)}}} g\\,d{var} = [h({var})]_{{{latex(lower)}}}^{{{latex(upper)}}} + 3[\\ln|{var}^2-9|]_{{{latex(lower)}}}^{{{latex(upper)}}}\\).",
         "formula": "antiderivative_reciprocal_ln"},
        {"title": "Apply the bounds",
         "detail": f"\\([h]_{{{latex(lower)}}}^{{{latex(upper)}}} = {inline_latex(h_upper)} - {inline_latex(h_lower)}\\).",
         "formula": "fundamental_theorem"},
        {"title": "Result",
         "detail": f"\\(S = {inline_latex(result)}\\) square units.", "formula": "fundamental_theorem"},
    ]
    checkpoints = [
        {"label": f"h({latex(upper)})", "value": h_upper, "formula": "product_rule"},
        {"label": f"h({latex(lower)})", "value": h_lower, "formula": "product_rule"},
        {"label": "area", "value": result, "formula": "fundamental_theorem"},
    ]
    try:
        decimal = float(N(result, 8))
    except Exception:
        decimal = None
    P, Q = _log_split(expr, x)
    gprime = simplify(diff(expr, x))
    ctx = {"lower": latex(lower), "upper": latex(upper), "value": latex(result),
           "value_plain": str(result), "shape": "log",
           "g": latex(expr), "gprime": latex(gprime), "split": f"{latex(log(P))} - {latex(log(Q))}",
           "P": latex(P), "Q": latex(Q), "h": latex(h), "h_upper": latex(h_upper), "h_lower": latex(h_lower),
           "fn": params.get("fn_name", "g"), "h_fn": part.get("h_fn", "h")}
    return _part_solution(part, result, latex(result), display, decimal, steps, checkpoints, ctx=ctx)


def _domain_intervals(expr, x):
    """Open intervals of the real domain of ``expr`` (log argument > 0, or
    rationals excluding denominator roots)."""
    if isinstance(expr, log):
        u = expr.args[0]
        return _positive_intervals(u, x)
    num, den = expr.as_numer_denom()
    poles = sorted(set(_f(r) for r in solve(den, x) if r.is_real))
    if not poles:
        return [{"lo": float("-inf"), "hi": float("inf"), "lo_open": True, "hi_open": True}]
    bounds = [float("-inf")] + poles + [float("inf")]
    return [{"lo": bounds[i], "hi": bounds[i + 1], "lo_open": True, "hi_open": True}
            for i in range(len(bounds) - 1)]


def _solve_part_monotonicity(params, x, expr, part):
    """BAC II 'study the variation of g': sign of g'(x) per domain interval and
    the resulting monotonicity verdict. The domain is split at critical points
    and vertical asymptotes first, so each reported segment is genuinely
    monotonic. Answer is the list of (interval, direction) pieces; checkpoints
    carry g'(x) and the critical points."""
    var = params["var"]
    der = simplify(diff(expr, x))
    crit = sorted(set(float(r) for r in solve(der, x) if r.is_real))
    dom = _domain_intervals(expr, x)
    bps = set()
    for iv in dom:
        if iv["lo"] != float("-inf"):
            bps.add(iv["lo"])
        if iv["hi"] != float("inf"):
            bps.add(iv["hi"])
    bps.update(crit)
    bps = sorted(bps)
    all_bp = []
    if any(iv["lo"] == float("-inf") for iv in dom):
        all_bp.append(float("-inf"))
    all_bp += bps
    if any(iv["hi"] == float("inf") for iv in dom):
        all_bp.append(float("inf"))
    pieces = []
    for i in range(len(all_bp) - 1):
        a, b = all_bp[i], all_bp[i + 1]
        if a == float("-inf"):
            mid = b - 1
        elif b == float("inf"):
            mid = a + 1
        else:
            mid = (a + b) / 2
        inside = any((iv["lo"] == float("-inf") or iv["lo"] < mid) and
                     (iv["hi"] == float("inf") or mid < iv["hi"]) for iv in dom)
        if not inside:
            continue
        s = simplify(der.subs(x, mid))
        if s.is_positive or (s.is_positive is None and float(N(s)) > 0):
            direction = "inc"
        elif s.is_negative or (s.is_negative is None and float(N(s)) < 0):
            direction = "dec"
        else:
            direction = "inc"
        seg = [{"lo": a, "hi": b, "lo_open": True, "hi_open": True}]
        pieces.append({"interval": _interval_display(seg), "direction": direction})
    disp_parts = []
    for p in pieces:
        word = "កើន" if p["direction"] == "inc" else "ចុះ"
        disp_parts.append(f"{word} លើ {p['interval']}")
    display = "; ".join(disp_parts) or "ថេរ"
    steps = [
        {"title": "Derivative", "detail": f"\\(g'({var}) = {inline_latex(der)}\\) .",
         "formula": "quotient_rule"},
        {"title": "Sign of the derivative",
         "detail": part.get("technique", "") or f"\\(g'({var})\\) keeps a constant sign on each interval between critical points / asymptotes.",
         "formula": "monotonicity_sign"},
        {"title": "Conclusion", "detail": f"\\(g\\) {display}.", "formula": "monotonicity_sign"},
    ]
    checkpoints = [{"label": f"g'({var})", "value": der, "formula": "quotient_rule"}]
    checkpoints += [{"label": f"critical {c}", "value": c, "formula": "monotonicity_sign"} for c in crit]
    ctx = {"pieces": [{"interval": p["interval"], "direction": p["direction"]} for p in pieces],
           "shape": "log", "der": latex(der)}
    return _part_solution(part, pieces, display, display, None, steps, checkpoints, ctx=ctx)


def _intersect_intervals(a, b):
    """Intersection of two lists of open intervals (all open)."""
    out = []
    for iv in a:
        for jv in b:
            lo = max(iv["lo"], jv["lo"])
            hi = min(iv["hi"], jv["hi"])
            if lo < hi:
                out.append({"lo": lo, "hi": hi, "lo_open": True, "hi_open": True})
    out.sort(key=lambda d: d["lo"])
    return out


def _solve_part_sign(params, x, expr, part):
    """Sign of g(x): intervals where g > 0 and where g < 0 (MoEYS asks 'study the
    sign of g(x) according to x'). Restricted to the real domain of g."""
    var = params["var"]
    dom = _domain_intervals(expr, x)
    if isinstance(expr, log):
        u = expr.args[0]
        # g>0 <=> u>1 ; g<0 <=> 0<u<1 (automatically inside the domain u>0)
        pos = _positive_intervals(u - 1, x)
        neg = _intersect_intervals(_positive_intervals(1 - u, x), dom)
    else:
        pos = _positive_intervals(expr, x)
        neg = _intersect_intervals(_positive_intervals(-expr, x), dom)
    pos_disp = _interval_display(pos) or "\\varnothing"
    neg_disp = _interval_display(neg) or "\\varnothing"
    display = f"g({var}) < 0 លើ {neg_disp} ; g({var}) > 0 លើ {pos_disp}"
    steps = [
        {"title": "Sign of g(x)",
         "detail": part.get("technique", "") or f"Study the sign of \\(g({var}) = {inline_latex(expr)}\\) on its domain.",
         "formula": "sign_table"},
        {"title": "Conclusion", "detail": display, "formula": "sign_table"},
    ]
    roots = sorted(set(_f(r) for r in solve(expr, x) if r.is_real))
    checkpoints = [{"label": f"root {r}", "value": r, "formula": "sign_table"} for r in roots]
    ctx = {"pos": pos_disp, "neg": neg_disp}
    return _part_solution(part, pos, display, display, None, steps, checkpoints, ctx=ctx)


def _solve_part_variation_table(params, x, expr, part):
    """The BAC II variation table: breakpoints (domain ends + critical points +
    vertical asymptotes), the sign of g'(x) on each segment, the limits/values
    of g at each breakpoint, and the monotonicity arrows. Returned as a JSON
    structure (``variation_table``) the frontend renders as a real table."""
    var = params["var"]
    der = simplify(diff(expr, x))
    dom = _domain_intervals(expr, x)
    crit = sorted(set(float(r) for r in solve(der, x) if r.is_real))
    bps = set()
    for iv in dom:
        if iv["lo"] != float("-inf"):
            bps.add(iv["lo"])
        if iv["hi"] != float("inf"):
            bps.add(iv["hi"])
    bps.update(crit)
    bps = sorted(bps)
    def _clean_b(b):
        if isinstance(b, (float, int)):
            if float(b).is_integer():
                return str(int(b))
        return str(b)

    cols = []
    if any(iv["lo"] == float("-inf") for iv in dom):
        cols.append("-∞")
    cols += [_clean_b(b) for b in bps]
    if any(iv["hi"] == float("inf") for iv in dom):
        cols.append("+∞")

    def col_val(label):
        if label == "-∞":
            return float("-inf")
        if label == "+∞":
            return float("inf")
        return float(sympify(label, locals=_calc_locals(var)))

    def func_at(label):
        if label == "-∞":
            return latex(limit(expr, x, -oo))
        if label == "+∞":
            return latex(limit(expr, x, oo))
        c = sympify(label, locals=_calc_locals(var))
        if any(abs(float(c) - b) < 1e-9 for b in crit):
            return latex(simplify(expr.subs(x, c)))
        from_left = any(abs(iv["hi"] - float(c)) < 1e-9 for iv in dom)
        from_right = any(abs(iv["lo"] - float(c)) < 1e-9 for iv in dom)
        if from_left and from_right:
            return f"{latex(limit(expr, x, c, dir='-'))} / {latex(limit(expr, x, c, dir='+'))}"
        if from_right:
            return latex(limit(expr, x, c, dir="+"))
        if from_left:
            return latex(limit(expr, x, c, dir="-"))
        return latex(simplify(expr.subs(x, c)))

    func_cells = [func_at(c) for c in cols]
    deriv_cells, arrows = [], []
    for i in range(len(cols) - 1):
        a, b = col_val(cols[i]), col_val(cols[i + 1])
        if a == float("-inf"):
            mid = (b - 1) if b != float("inf") else 0
        elif b == float("inf"):
            mid = a + 1
        else:
            mid = (a + b) / 2
        s = simplify(der.subs(x, mid))
        if s.is_positive or (s.is_positive is None and float(N(s)) > 0):
            sign = "+"
        elif s.is_negative or (s.is_negative is None and float(N(s)) < 0):
            sign = "-"
        else:
            sign = "0"
        deriv_cells.append(sign)
        arrows.append("↗" if sign == "+" else ("↘" if sign == "-" else "–"))

    extrema = []
    for c in crit:
        ci = col_val(str(c))
        left = next((d for i, d in enumerate(deriv_cells) if cols[i + 1] == str(c)), None)
        right = next((d for i, d in enumerate(deriv_cells) if cols[i] == str(c)), None)
        if left and right and left != right:
            etype = "min" if left == "-" and right == "+" else "max"
            extrema.append({"x": str(c), "type": etype, "value": latex(simplify(expr.subs(x, c)))})

    table = {
        "columns": cols,
        "derivative_sign": deriv_cells,
        "arrows": arrows,
        "func_values": func_cells,
        "extrema": extrema,
    }
    display = "variation table"
    steps = [
        {"title": "Variation table",
         "detail": part.get("technique", "") or "Compile the sign of \\(g'(x)\\) and the limits into the variation table.",
         "formula": "monotonicity_sign"},
    ]
    checkpoints = [{"label": f"g'({var})", "value": der, "formula": "quotient_rule"}]
    for c in crit:
        checkpoints.append({"label": f"f({c})", "value": simplify(expr.subs(x, c)), "formula": "monotonicity_sign"})
    for iv in dom:
        for bd in (iv["lo"], iv["hi"]):
            if bd not in (float("-inf"), float("inf")):
                checkpoints.append({"label": f"lim {var}->{bd}",
                                    "value": limit(expr, x, sympify(bd, locals=_calc_locals(var))),
                                    "formula": "vertical_asymptote"})
    sol = _part_solution(part, table, display, display, None, steps, checkpoints)
    sol["variation_table"] = table
    sol["_ctx"] = {"table": table}
    return sol


def _build_graph(params, x, expr):
    """JSON-safe reference-graph spec: curve sampled in segments split at the
    vertical asymptotes, the tangent line (two points), asymptote x-values,
    labeled points, and the plotting window. The frontend draws it as SVG."""
    g = params.get("graph") or {}
    x_min = float(g.get("x_min", -6))
    x_max = float(g.get("x_max", 6))
    y_min = float(g.get("y_min", -6))
    y_max = float(g.get("y_max", 6))
    n = int(g.get("samples", 200))
    asymptotes = [float(a["x"]) for a in g.get("asymptotes", []) if a.get("kind") == "vertical"]
    cut_points = sorted(p for p in asymptotes if x_min < p < x_max)
    breaks = sorted(set([x_min] + cut_points + [x_max]))
    margin = (y_max - y_min) * 0.5
    segments = []
    for i in range(len(breaks) - 1):
        lo, hi = breaks[i], breaks[i + 1]
        if hi - lo < 1e-9:
            continue
        pts = []
        for j in range(n):
            xv = lo + (hi - lo) * j / (n - 1)
            yv = N(expr.subs(x, xv))
            if not yv.is_real or not yv.is_finite:
                continue
            yf = float(yv)
            if yf < y_min - margin or yf > y_max + margin:
                continue
            pts.append([round(xv, 6), round(yf, 6)])
        if len(pts) >= 2:
            segments.append(pts)

    tangents = []
    t_list = g.get("tangents") if isinstance(g.get("tangents"), list) else ([g["tangent"]] if g.get("tangent") else [])
    for t in t_list:
        var = params["var"]
        x0 = sympify(t["x0"], locals=_calc_locals(var))
        y0 = simplify(expr.subs(x, x0))
        m = simplify(diff(expr, x).subs(x, x0))
        span = x_max - x_min
        xa = float(x0) - span * 0.4
        xb = float(x0) + span * 0.4
        ya = float(simplify(y0 + m * (sympify(xa) - x0)))
        yb = float(simplify(y0 + m * (sympify(xb) - x0)))
        tangents.append([[round(xa, 4), round(ya, 4)], [round(xb, 4), round(yb, 4)]])
    tangent = tangents[0] if tangents else None

    asymptote_lines = []
    for a in g.get("asymptotes", []):
        kind = a.get("kind")
        if kind not in ("oblique", "horizontal"):
            continue
        var = params["var"]
        line = sympify(a["line"], locals=_calc_locals(var))
        span = x_max - x_min
        xa = x_min - 0.1 * span
        xb = x_max + 0.1 * span
        ya = float(simplify(line.subs(x, sympify(xa))))
        yb = float(simplify(line.subs(x, sympify(xb))))
        asymptote_lines.append({
            "kind": kind,
            "points": [[round(xa, 4), round(ya, 4)], [round(xb, 4), round(yb, 4)]],
            "line": latex(line),
            "label": a.get("label", f"y = {latex(line)}"),
        })

    points = [{"x": float(p["x"]), "y": float(p["y"]), "label": p.get("label", "")} for p in g.get("points", [])]
    return {
        "x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max,
        "curve": segments, "vertical_asymptotes": asymptotes,
        "tangent": tangent, "tangents": tangents, "asymptote_lines": asymptote_lines,
        "points": points,
    }


def _solve_function_study(params):
    var = params["var"]
    x = Symbol(var)
    expr = sympify(params["function_expr"], locals=_calc_locals(var))
    part_solutions = []
    en_blocks = []
    km_facts = {"parts": []}
    for part in params.get("parts", []):
        want = part.get("want")
        if want == "domain":
            sol = _solve_part_domain(params, x, expr, part)
        elif want == "parity":
            sol = _solve_part_parity(params, x, expr, part)
        elif want == "limit":
            sol = _solve_part_limit(params, x, expr, part)
        elif want == "limits":
            sol = _solve_part_limits(params, x, expr, part)
        elif want == "draw":
            sol = _solve_part_draw(params, x, expr, part)
        elif want == "derivative":
            sol = _solve_part_derivative(params, x, expr, part)
        elif want == "variation":
            sol = _solve_part_variation(params, x, expr, part)
        elif want == "asymptote":
            sol = _solve_part_asymptote(params, x, expr, part)
        elif want == "decompose":
            sol = _solve_part_decompose(params, x, expr, part)
        elif want == "position":
            sol = _solve_part_position(params, x, expr, part)
        elif want == "symmetry":
            sol = _solve_part_symmetry(params, x, expr, part)
        elif want == "tangent":
            sol = _solve_part_tangent(params, x, expr, part)
        elif want == "derivative_product":
            sol = _solve_part_derivative_product(params, x, expr, part)
        elif want == "integral":
            sol = _solve_part_integral(params, x, expr, part)
        elif want == "monotonicity":
            sol = _solve_part_monotonicity(params, x, expr, part)
        elif want == "variation_table":
            sol = _solve_part_variation_table(params, x, expr, part)
        elif want == "sign":
            sol = _solve_part_sign(params, x, expr, part)
        else:
            raise ValueError(f"unknown function-study want: {want}")
        for cp in part.get("extra_checkpoints") or []:
            val = simplify(sympify(cp["value"], locals=_calc_locals(var)))
            sol["checkpoints"].append({"label": cp["label"], "value": val,
                                       "formula": cp.get("formula", "monotonicity_sign")})
        sol["checkpoints"] = [{**cp, "label": f"{sol['label']}: {cp['label']}"} for cp in sol["checkpoints"]]
        sol["steps"] = [{**s, "title": f"Part {sol['label']}: {s['title']}"} for s in sol["steps"]]

        ctx = sol.get("_ctx") or {}
        fn_name = params.get("fn_name", "f")
        # Khmer writing is no longer templated: it is generated by Gemini from
        # these SymPy-locked facts (see engine/llm.narrate_km_solution). The
        # displayed answer line falls back to the English/math render so the UI
        # never shows hard-coded Khmer prose.
        ans_disp = part.get("display") or render_answer(want, ctx, var, fn_name, lang="en") or sol.get("answer_display")
        en_disp = part.get("display_en") or render_answer(want, ctx, var, fn_name, lang="en") or ans_disp
        sol["answer_display"] = ans_disp
        sol["answer_display_en"] = en_disp

        q_km = part.get("question_km") or ""
        q_en = part.get("question_en") or render_question(want, ctx, var, fn_name) or ""
        technique_km = part.get("technique") or ""
        technique_en = part.get("technique_en") or "\n".join(render_steps(want, ctx, var, fn_name, lang="en")) or ""
        sol["question_km"] = q_km
        sol["question_en"] = q_en
        sol["technique"] = technique_km
        sol["technique_en"] = technique_en

        en_block = ""
        if q_en:
            en_block += f"**{sol['label']}** {q_en}\n\n"
        if technique_en:
            en_block += "\n".join(t.strip() for t in technique_en.split("\n") if t.strip()) + "\n\n"
        en_block += f"Answer: {en_disp}"

        en_blocks.append(en_block)

        km_facts["parts"].append({
            "label": sol["label"],
            "question_km": q_km,
            "steps": [{"title": s["title"], "latex": s["detail"]} for s in sol["steps"]],
            "answer_latex": sol["answer_latex"] or sol.get("answer_display") or "",
        })
        part_solutions.append(sol)

    merged_cps = [cp for sol in part_solutions for cp in sol["checkpoints"]]
    merged_steps = [s for sol in part_solutions for s in sol["steps"]]
    tags = list(dict.fromkeys(t for sol in part_solutions for t in sol["formula_tags"]))
    target = part_solutions[-1]
    return {
        "answer_exact": target["answer_exact"],
        "answer_decimal": target["answer_decimal"],
        "answer_latex": target["answer_latex"],
        "answer_display": target.get("answer_display"),
        "answer_display_en": target.get("answer_display_en"),
        "steps": merged_steps,
        "formula_tags": tags,
        "checkpoints": merged_cps,
        "parts": part_solutions,
        "target_label": target["label"],
        "work_mode": "any_order",
        "given": expr,
        "graph": _build_graph(params, x, expr),
        "solution_km": None,
        "km_facts": km_facts,
        "solution_en": "\n\n".join(en_blocks),
    }