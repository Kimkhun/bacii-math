"""Function-study solvers: multi-part BAC II exercises built from one function
g(x) — domain, parity, one-sided limits, tangent line, derivative of a product,
and an area integral. SymPy computes every answer; the curated exercise card
(backend/data/functions/*.json) supplies the MoEYS narration text. Assembly
mirrors solver/probability.py's multi-part pattern (work_mode "any_order",
part-labeled steps and checkpoints, target = last part)."""
from sympy import N, Symbol, diff, div, integrate, latex, limit, log, logcombine, oo, simplify, solve, sympify

from .shared import _calc_locals, _formula_tags, inline_latex


def _f(v):
    """SymPy number -> float (∞ -> inf, -∞ -> -inf)."""
    if v == oo:
        return float("inf")
    if v == -oo:
        return float("-inf")
    return float(N(v, 8))


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


def _part_solution(part, answer_exact, answer_latex, answer_display, answer_decimal, steps, checkpoints):
    return {
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
        "exact_only": part.get("exact_only", False),
    }


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
        return _part_solution(part, ivs, display, display, None, steps, checkpoints)

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
    return _part_solution(part, ivs, display, display, None, steps, checkpoints)


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
    return _part_solution(part, verdict, display, display, None, steps, checkpoints)


def _solve_part_limit(params, x, expr, part):
    var = params["var"]
    point = sympify(part["point"], locals=_calc_locals(var))
    side = part.get("side")
    result = limit(expr, x, point, dir=side) if side else limit(expr, x, point)
    point_latex = latex(point) + ("^+" if side == "+" else "^-" if side == "-" else "")
    display = part.get("display") or (latex(result) if result in (oo, -oo) else str(result))
    steps = [
        {"title": "Set up the one-sided limit",
         "detail": f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr)}\\).",
         "formula": "setup_limit"},
        {"title": "Evaluate the direction", "detail": part.get("technique", ""), "formula": "vertical_asymptote"},
        {"title": "Result", "detail": f"The limit is {inline_latex(result)}.", "formula": "vertical_asymptote"},
    ]
    checkpoints = [{"label": "limit", "value": result, "formula": "vertical_asymptote"}]
    decimal = None if result in (oo, -oo) else _f(result)
    return _part_solution(part, result, latex(result), display, decimal, steps, checkpoints)


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
         "detail": f"\\(f({var}) = {inline_latex(expr)}\\).",
         "formula": "setup_limit"},
        {"title": "Evaluate each",
         "detail": part.get("technique", "") or f"\\({summary}\\).",
         "formula": "vertical_asymptote"},
        {"title": "Conclusion",
         "detail": f"\\({summary}\\).", "formula": "vertical_asymptote"},
    ]
    checkpoints = [
        {"label": f"lim {var}->{r['point']}", "value": r["value"], "formula": "vertical_asymptote"}
        for r in results
    ]
    decimal = None if answer in (oo, -oo) else _f(answer)
    return _part_solution(part, answer, latex(answer), display, decimal, steps, checkpoints)


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
    return _part_solution(part, answer, latex(answer), display, None, steps, checkpoints)


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
    return _part_solution(part, der, latex(der), display, None, steps, checkpoints)


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
    return _part_solution(part, line, latex(line), display, None, steps, checkpoints)


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
         "detail": f"Divide \\({inline_latex(num)}\\) by \\({inline_latex(den)}\\).",
         "formula": "euclidean_division"},
        {"title": "Quotient and remainder",
         "detail": f"Quotient \\(q(x) = {inline_latex(q)}\\), remainder \\(r = {inline_latex(r)}\\), so \\(f(x) = {inline_latex(dec)}\\).",
         "formula": "euclidean_division"},
        {"title": "Identify a, b, c",
         "detail": f"\\(a = {inline_latex(a)}\\), \\(b = {inline_latex(b)}\\), \\(c = {inline_latex(c)}\\).",
         "formula": "euclidean_division"},
    ]
    checkpoints = [
        {"label": "decomposition", "value": dec, "formula": "euclidean_division"},
        {"label": "a", "value": a, "formula": "euclidean_division"},
        {"label": "b", "value": b, "formula": "euclidean_division"},
        {"label": "c", "value": c, "formula": "euclidean_division"},
    ]
    return _part_solution(part, dec, latex(dec), display, None, steps, checkpoints)


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
    return _part_solution(part, ivs, display, display, None, steps, checkpoints)


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
    return _part_solution(part, target, latex(target), display, None, steps, checkpoints)


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
    return _part_solution(part, line, latex(line), display, None, steps, checkpoints)


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
    return _part_solution(part, der, latex(der), display, None, steps, checkpoints)


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
    return _part_solution(part, result, latex(result), display, decimal, steps, checkpoints)


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
        else:
            raise ValueError(f"unknown function-study want: {want}")
        for cp in part.get("extra_checkpoints") or []:
            val = simplify(sympify(cp["value"], locals=_calc_locals(var)))
            sol["checkpoints"].append({"label": cp["label"], "value": val,
                                       "formula": cp.get("formula", "monotonicity_sign")})
        sol["checkpoints"] = [{**cp, "label": f"{sol['label']}: {cp['label']}"} for cp in sol["checkpoints"]]
        sol["steps"] = [{**s, "title": f"Part {sol['label']}: {s['title']}"} for s in sol["steps"]]
        part_solutions.append(sol)

    merged_cps = [cp for sol in part_solutions for cp in sol["checkpoints"]]
    merged_steps = [s for sol in part_solutions for s in sol["steps"]]
    tags = list(dict.fromkeys(t for sol in part_solutions for t in sol["formula_tags"]))
    target = part_solutions[-1]
    return {
        "answer_exact": target["answer_exact"],
        "answer_decimal": target["answer_decimal"],
        "answer_latex": target["answer_latex"],
        "steps": merged_steps,
        "formula_tags": tags,
        "checkpoints": merged_cps,
        "parts": part_solutions,
        "target_label": target["label"],
        "work_mode": "any_order",
        "given": expr,
        "graph": _build_graph(params, x, expr),
    }