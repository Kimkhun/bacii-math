"""Limit solver: per-technique step handlers, plus a generic ``formula_name``-keyed
branch (``_curated_limit_steps``) shared by every procedurally-generated structure."""
from sympy import (
    N,
    Pow,
    Rational,
    S,
    Symbol,
    cancel,
    cos,
    degree,
    diff,
    exp,
    expand,
    factor,
    latex,
    limit,
    log,
    oo,
    simplify,
    sin,
    sqrt,
    sympify,
)

from ...core.shared import _calc_locals, _formula_tags, inline_latex


def _limit_step(title, detail, formula):
    if isinstance(detail, str):
        detail = detail.replace(r"\log", r"\ln")
    return {"title": "", "detail": detail, "formula": None}


def _has_radical(e):
    return any(isinstance(a, Pow) and not a.exp.is_integer for a in e.atoms(Pow))


def _rationalization_conjugate_checkpoints(x, point, expr, formula):
    """Derive the intermediate "cancelled form" checkpoint for a 0/0 limit
    where exactly one of numerator/denominator carries a square root: rationalize
    that side by its conjugate, cancel the shared (x - point) factor against the
    other (polynomial) side, and report the resulting expression. Generalizes the
    `rationalization_conjugate_finite` family (whichever side — numerator or
    denominator — the sqrt is on, and any leading constant multiplier)
    instead of hardcoding each one. Returns [] when the shape
    doesn't match (e.g. both sides have a radical), leaving the caller with
    just the final-value checkpoint."""
    def _conjugate_factor(e):
        terms = e.as_ordered_terms()
        if len(terms) == 2:
            return terms[0] - terms[1]
        sqrt_terms = sum(t for t in terms if _has_radical(t))
        other_terms = sum(t for t in terms if not _has_radical(t))
        return other_terms - sqrt_terms

    try:
        num, den = expr.as_numer_denom()
        has_num_rad = _has_radical(num)
        has_den_rad = _has_radical(den)

        if has_num_rad and not has_den_rad:
            conjugate = _conjugate_factor(num)
            rationalized = expand(num * conjugate)
            reduced = cancel(rationalized / den)
            cancelled = reduced / conjugate
        elif has_den_rad and not has_num_rad:
            conjugate = _conjugate_factor(den)
            rationalized = expand(den * conjugate)
            reduced = cancel(num / rationalized)
            cancelled = reduced * conjugate
        elif has_num_rad and has_den_rad:
            c_num = _conjugate_factor(num)
            c_den = _conjugate_factor(den)
            rat_num = expand(num * c_num)
            rat_den = expand(den * c_den)
            reduced_poly = cancel(rat_num / rat_den)
            cancelled = reduced_poly * c_den / c_num
        else:
            return []

        if simplify(cancelled.subs(x, point) - limit(expr, x, point)) != 0:
            return []
    except Exception:
        return []
    return [{"label": "cancelled form", "value": cancelled, "formula": formula}]


# formula_names whose parameterized handler (below) computes its checkpoints
# purely from (x, point, expr) — no technique-specific params like a sampled
# instance's k/a/d — so the same handler covers every sampled shape for that
# technique.
_CURATED_REUSABLE_HANDLERS = {"direct_substitution", "factoring_0_0", "rational_function_infinity"}


def _exponential_standard_limit_checkpoints(x, point, expr, formula):
    """Derive the two intermediate "divide by the variable, apply the
    standard exponential limit separately" checkpoints for a 0/0 limit shaped
    like (e^{ax}-1)/(e^{bx}-1) at x=0: the numerator and denominator each
    divided by x and limited on their own (giving a and b respectively).
    Purely generic on `expr` — no a/b params needed — so it covers every
    sampled instance, whatever the exact coefficients. Returns [] when the
    denominator's own limit is 0 (shape doesn't apply)."""
    try:
        num, den = expr.as_numer_denom()
        num_lim = limit(num / x, x, point)
        den_lim = limit(den / x, x, point)
        if den_lim == 0:
            return []
        if simplify(num_lim / den_lim - limit(expr, x, point)) != 0:
            return []
    except Exception:
        return []
    return [
        {"label": "numerator limit", "value": num_lim, "formula": formula},
        {"label": "denominator limit", "value": den_lim, "formula": formula},
    ]


def _one_infinity_checkpoints(x, point, expr, formula):
    """Derive intermediate checkpoint for 1^infinity forms f(x)^g(x):
    the limit of the exponent g(x) * (f(x) - 1). If finite, students
    writing this exponent limit get credited intermediate progress."""
    try:
        base, pwr = expr.as_base_exp()
        L = limit(pwr * (base - 1), x, point)
        if L is not None and not L.has(Symbol):
            return [{"label": "exponent limit", "value": L, "formula": formula}]
    except Exception:
        return []
    return []


def _logarithmic_standard_limit_checkpoints(x, point, expr, formula):
    """Derive intermediate checkpoints for logarithmic limits:
    1. If expr has ln(g(x)), check if inside limit lim(g(x)) exists and is positive.
    2. If expr is a fraction num/den, check separated numerator and denominator limits."""
    cps = []
    try:
        ln_atoms = [arg for arg in expr.atoms(log)]
        for log_expr in ln_atoms:
            inside = log_expr.args[0]
            inside_lim = limit(inside, x, point)
            if inside_lim is not None and not inside_lim.has(Symbol) and inside_lim > 0:
                cps.append({"label": "inside logarithm limit", "value": inside_lim, "formula": formula})
                break

        if point == 0:
            num, den = expr.as_numer_denom()
            if den != 1:
                num_lim = limit(num / x, x, point)
                den_lim = limit(den / x, x, point)
                if den_lim != 0 and num_lim is not None and not num_lim.has(Symbol) and not den_lim.has(Symbol):
                    if simplify(num_lim / den_lim - limit(expr, x, point)) == 0:
                        cps.append({"label": "numerator limit", "value": num_lim, "formula": formula})
                        cps.append({"label": "denominator limit", "value": den_lim, "formula": formula})
    except Exception:
        pass
    return cps


def _one_sided_radical_steps(kind, params, var, x, point_latex, expr, result):
    k = params.get("k", 1)
    kpre = f"{k}" if k != 1 else ""
    if kind == "half":
        reduced = k * sqrt(2) / (2 * sin(x / 2))
        steps = [
            _limit_step(
                "",
                rf"\[ \lim_{{{var} \to \pi^-}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
                None,
            ),
            _limit_step(
                "",
                rf"\[ = \lim_{{{var} \to \pi^-}} \dfrac{{\sqrt{{2\cos^2\frac{{{var}}}{{2}}}}}}{{2\sin\frac{{{var}}}{{2}}\cos\frac{{{var}}}{{2}}}} \]",
                None,
            ),
            _limit_step(
                "",
                rf"\[ = \lim_{{{var} \to \pi^-}} {kpre}\dfrac{{\sqrt{{2}}}}{{2\sin\frac{{{var}}}{{2}}}} = {latex(result)} \]",
                None,
            ),
        ]
    else:
        reduced = k * sqrt(2) / (2 * cos(x))
        steps = [
            _limit_step(
                "",
                rf"\[ \lim_{{{var} \to \pi^-}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
                None,
            ),
            _limit_step(
                "",
                rf"\[ = \lim_{{{var} \to \pi^-}} \dfrac{{\sqrt{{2\sin^2 {var}}}}}{{2\sin {var}\cos {var}}} \]",
                None,
            ),
            _limit_step(
                "",
                rf"\[ = \lim_{{{var} \to \pi^-}} {kpre}\dfrac{{\sqrt{{2}}}}{{2\cos {var}}} = {latex(result)} \]",
                None,
            ),
        ]
    return steps, reduced



_ONE_SIDED_RADICAL_KINDS = {
    "limit:trig:radical_cos_sin_pi": "half",
    "limit:trig:radical_cos2x_sin2x_pi": "double",
}


# Above this exponent the "simplify to ..." narration is skipped. Year-style exponents
# ((x**2023 + 1)/(x**2015 + 1)) cancel to a ~2,000-term quotient that simplify() does not
# finish in any useful time, pinning a worker thread (a thread cannot be killed, so it
# outlives the request timeout), and that quotient is no help to a student anyway.
_MAX_NARRATED_EXPONENT = 20


def _has_huge_power(expr):
    return any(p.exp.is_Integer and abs(p.exp) > _MAX_NARRATED_EXPONENT for p in expr.atoms(Pow))


def _derived_technique_text(formula, var, x, point_latex, expr):
    """Narration for a limit that has no authored technique text (exercises built
    from technique templates): the technique's catalogue name plus, when SymPy
    can simplify the expression, that simplification.
    Never blank, and only says what SymPy actually computed."""
    from engine.formulas import resolve_formula

    parts = []
    name = (resolve_formula(formula).get("name_en") or "").strip()
    if name and name != formula:
        parts.append(f"{name}.")
    try:
        simplified = expr if _has_huge_power(expr) else simplify(cancel(expr))
        if simplified != expr:
            parts.append(
                f"Simplify \\({latex(expr, ln_notation=True)}\\) to "
                f"\\({latex(simplified, ln_notation=True)}\\) before taking the limit."
            )
    except Exception:
        pass
    if not parts:
        parts.append(f"Evaluate \\(\\lim_{{{var} \\to {point_latex}}}\\) with the technique for this form.")
    return " ".join(parts)


def _rational_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula):
    if point in (oo, -oo):
        return _handle_rational_function_infinity(params, var, x, point, point_latex, expr, result)

    try:
        num, den = expr.as_numer_denom()
        deg_num = degree(num, x) if (hasattr(num, "is_polynomial") and num.is_polynomial(x)) else 1
        deg_den = degree(den, x) if (hasattr(den, "is_polynomial") and den.is_polynomial(x)) else 1

        # High-degree polynomials (e.g. (x^2019 + 1)/(x^2015 + 1))
        # Avoid polynomial expansion blowout! Use the standard power derivative identity:
        # lim_{x->a} (x^n - a^n)/(x - a) = n*a^(n-1)
        if deg_num > 6 or deg_den > 6:
            steps = [
                _limit_step(
                    "",
                    rf"\[ \lim_{{{var} \to {point_latex}}} \dfrac{{{latex(num)}}}{{{latex(den)}}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
                    None,
                ),
                _limit_step(
                    "",
                    rf"\[ \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{\frac{{{latex(num)}}}{{{var} - ({point_latex})}}}}{{\frac{{{latex(den)}}}{{{var} - ({point_latex})}}}} \]",
                    None,
                ),
            ]
            d_num = diff(num, x)
            d_den = diff(den, x)
            val_num = d_num.subs(x, point)
            val_den = d_den.subs(x, point)
            steps.append(_limit_step(
                "",
                rf"\[ \lim_{{{var} \to {point_latex}}} \dfrac{{{latex(num)}}}{{{var} - ({point_latex})}} = {latex(val_num)}, \quad \lim_{{{var} \to {point_latex}}} \dfrac{{{latex(den)}}}{{{var} - ({point_latex})}} = {latex(val_den)} \]",
                None,
            ))
            steps.append(_limit_step(
                "",
                rf"\[ \lim_{{{var} \to {point_latex}}} \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{{latex(val_num)}}}{{{latex(val_den)}}} = {latex(result)} \]",
                None,
            ))
            checkpoints = [
                {"label": "numerator limit", "value": val_num, "formula": "limit_power_identity"},
                {"label": "denominator limit", "value": val_den, "formula": "limit_power_identity"},
                {"label": "final value", "value": result, "formula": "limit_power_identity"},
            ]
            return steps, checkpoints

        cancelled = cancel(num / den)
        if cancelled == expr:
            return None

        sub_val = simplify(cancelled.subs(x, point))

        steps = [
            _limit_step(
                "",
                rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
                None,
            ),
        ]
        checkpoints = []

        try:
            num_f = factor(num)
            den_f = factor(den)
            steps.append(_limit_step(
                "",
                rf"\[ = \dfrac{{{latex(num_f)}}}{{{latex(den_f)}}} \]",
                None,
            ))
            checkpoints.append({"label": "factored form", "value": num_f / den_f, "formula": formula})
        except Exception:
            pass

        steps.append(_limit_step(
            "",
            rf"\[ = {latex(cancelled)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ \lim_{{{var} \to {point_latex}}} {latex(cancelled)} = {latex(sub_val)} \]",
            None,
        ))
        checkpoints.extend([
            {"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"},
            {"label": "final value", "value": result, "formula": "direct_substitution"},
        ])
        return steps, checkpoints
    except Exception:
        return None


def _radical_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula):
    try:
        num, den = expr.as_numer_denom()

        # Check for split radicals: numerator has sum/difference of radicals that can be separated
        terms = [t for t in num.as_ordered_terms() if t.has(x) and _has_radical(t)]
        if len(terms) >= 2 and not _has_radical(den):
            sub_limits = []
            steps = [
                _limit_step(
                    "",
                    rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
                    None,
                )
            ]
            branch_strs = []
            for t in terms:
                L_t = limit(t, x, point)
                branch = (t - L_t) / den
                L_branch = limit(branch, x, point)
                sub_limits.append(L_branch)
                sign_str = f"- {abs(L_t)}" if L_t >= 0 else f"+ {abs(L_t)}"
                branch_strs.append(rf"\dfrac{{{latex(t)} {sign_str}}}{{{latex(den)}}}")

            steps.append(_limit_step(
                "",
                rf"\[ = {' + '.join(branch_strs)} \]",
                None,
            ))
            steps.append(_limit_step(
                "",
                rf"\[ = {' + '.join(latex(val) for val in sub_limits)} = {latex(result)} \]",
                None,
            ))
            checkpoints = [{"label": "final value", "value": result, "formula": formula}]
            return steps, checkpoints

        # Check for cube root single radical: A^(1/3) - B
        cbrt_atoms = [a for a in expr.atoms(Pow) if a.exp == Rational(1, 3)]
        if cbrt_atoms:
            steps = [
                _limit_step(
                    "",
                    rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
                    None,
                ),
                _limit_step(
                    "",
                    rf"\[ = {latex(result)} \]",
                    None,
                ),
            ]
            checkpoints = [{"label": "final value", "value": result, "formula": formula}]
            return steps, checkpoints

        # Check for ratio of powers / nth roots at 1
        if point == 1 and expr.has(Pow):
            steps = [
                _limit_step(
                    "",
                    rf"\[ \lim_{{{var} \to 1}} \dfrac{{{latex(num)}}}{{{latex(den)}}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
                    None,
                ),
                _limit_step(
                    "",
                    rf"\[ = \lim_{{{var} \to 1}} \dfrac{{\frac{{{latex(num)}}}{{{var} - 1}}}}{{\frac{{{latex(den)}}}{{{var} - 1}}}} = {latex(result)} \]",
                    None,
                ),
            ]
            checkpoints = [{"label": "final value", "value": result, "formula": formula}]
            return steps, checkpoints

        # Check standard square-root conjugate checkpoints
        cps = _rationalization_conjugate_checkpoints(x, point, expr, formula)
        if cps:
            cancelled = cps[0]["value"]
            steps = [
                _limit_step(
                    "",
                    rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
                    None,
                ),
                _limit_step(
                    "",
                    rf"\[ = \lim_{{{var} \to {point_latex}}} {latex(cancelled)} \]",
                    None,
                ),
                _limit_step(
                    "",
                    rf"\[ = {latex(result)} \]",
                    None,
                ),
            ]
            checkpoints = [
                {"label": "cancelled form", "value": cancelled, "formula": formula},
                {"label": "final value", "value": result, "formula": formula},
            ]
            return steps, checkpoints

    except Exception:
        pass

    # Generic radical fallback
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {latex(result)} \]",
            None,
        ),
    ]

    checkpoints = [{"label": "final value", "value": result, "formula": formula}]
    return steps, checkpoints


def _sakhon_trig_steps(formula, params, var, expr, result):
    steps = []
    checkpoints = [{"label": "final value", "value": result, "formula": formula}]

    if formula == "limit:trig:sinc_linear_combo":
        c1 = params.get("c1", 3)
        c2 = params.get("c2", 2)
        c3 = params.get("c3", 1)
        k1 = params.get("k1", 1)
        k2 = params.get("k2", 2)
        k3 = params.get("k3", 3)
        t1 = f"{c1}\\sin {var}" if k1 == 1 else f"{c1}\\sin({k1}{var})"
        t2 = f"{c2}\\sin({k2}{var})" if c2 != 1 else f"\\sin({k2}{var})"
        t3 = f"{c3}\\sin({k3}{var})" if c3 != 1 else f"\\sin({k3}{var})"
        steps.append(_limit_step(
            "",
            rf"\[ A = \lim_{{{var} \to 0}} \dfrac{{{t1} - {t2} + {t3}}}{{{var}}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{{t1}}}{{{var}}} - \lim_{{{var} \to 0}} \dfrac{{{t2}}}{{{var}}} + \lim_{{{var} \to 0}} \dfrac{{{t3}}}{{{var}}} \]",
            None,
        ))
        k1_term = rf"{c1}\lim_{{{var} \to 0}} \dfrac{{\sin {var}}}{{{var}}}" if k1 == 1 else rf"{c1 * k1}\lim_{{{var} \to 0}} \dfrac{{\sin({k1}{var})}}{{{k1}{var}}}"
        k2_term = rf"{c2 * k2}\lim_{{{var} \to 0}} \dfrac{{\sin({k2}{var})}}{{{k2}{var}}}"
        k3_term = rf"{c3 * k3}\lim_{{{var} \to 0}} \dfrac{{\sin({k3}{var})}}{{{k3}{var}}}"
        steps.append(_limit_step(
            "",
            rf"\[ = {k1_term} - {k2_term} + {k3_term} = {c1*k1} - {c2*k2} + {c3*k3} = {latex(result)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ A = \lim_{{{var} \to 0}} \dfrac{{{t1} - {t2} + {t3}}}{{{var}}} = {latex(result)} \]",
            None,
        ))
        return steps, checkpoints

    if formula == "limit:trig:sinc_triple_product":
        a = params.get("a", 2)
        b = params.get("b", 3)
        c = params.get("c", 4)
        steps.append(_limit_step(
            "",
            rf"\[ B = \lim_{{{var} \to 0}} \dfrac{{\sin({a}{var})\sin({b}{var})\sin({c}{var})}}{{{var}^3}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{\sin({a}{var})}}{{{var}}} \times \lim_{{{var} \to 0}} \dfrac{{\sin({b}{var})}}{{{var}}} \times \lim_{{{var} \to 0}} \dfrac{{\sin({c}{var})}}{{{var}}} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = {a}\lim_{{{var} \to 0}} \dfrac{{\sin({a}{var})}}{{{a}{var}}} \times {b}\lim_{{{var} \to 0}} \dfrac{{\sin({b}{var})}}{{{b}{var}}} \times {c}\lim_{{{var} \to 0}} \dfrac{{\sin({c}{var})}}{{{c}{var}}} = {a} \times {b} \times {c} = {latex(result)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ B = \lim_{{{var} \to 0}} \dfrac{{\sin({a}{var})\sin({b}{var})\sin({c}{var})}}{{{var}^3}} = {latex(result)} \]",
            None,
        ))
        return steps, checkpoints

    if formula == "limit:trig:sinc_quadratic_combo":
        a = params.get("a", 3)
        b = params.get("b", 5)
        d = params.get("d", 7)
        steps.append(_limit_step(
            "",
            rf"\[ C = \lim_{{{var} \to 0}} \dfrac{{\sin^2({a}{var}) + {var}\sin({b}{var})}}{{{d}{var}^2}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \dfrac{{1}}{{{d}}} \lim_{{{var} \to 0}} \left( \dfrac{{\sin^2({a}{var})}}{{{var}^2}} + \dfrac{{\sin({b}{var})}}{{{var}}} \right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \dfrac{{1}}{{{d}}} \lim_{{{var} \to 0}} \left[ \left(\dfrac{{\sin({a}{var})}}{{{a}{var}}} \times {a}\right)^2 + \dfrac{{\sin({b}{var})}}{{{b}{var}}} \times {b} \right] = \dfrac{{{a**2} + {b}}}{{{d}}} = {latex(result)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ C = \lim_{{{var} \to 0}} \dfrac{{\sin^2({a}{var}) + {var}\sin({b}{var})}}{{{d}{var}^2}} = {latex(result)} \]",
            None,
        ))
        return steps, checkpoints

    if formula == "limit:trig:sinc_power_sum":
        a = params.get("a", 1)
        b = params.get("b", 2)
        p = params.get("p", 3)
        steps.append(_limit_step(
            "",
            rf"\[ D = \lim_{{{var} \to 0}} \dfrac{{\sin^{{{p}}}({a}{var}) + \sin^{{{p}}}({b}{var})}}{{{var}^{{{p}}}}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \left( \dfrac{{\sin^{{{p}}}({a}{var})}}{{{var}^{{{p}}}}} + \dfrac{{\sin^{{{p}}}({b}{var})}}{{{var}^{{{p}}}}} \right) \]",
            None,
        ))
        term_a = rf"\left(\dfrac{{\sin {var}}}{{{var}}}\right)^{{{p}}}" if a == 1 else rf"\left(\dfrac{{\sin({a}{var})}}{{{a}{var}}} \times {a}\right)^{{{p}}}"
        term_b = rf"\left(\dfrac{{\sin({b}{var})}}{{{b}{var}}} \times {b}\right)^{{{p}}}"
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \left[ {term_a} + {term_b} \right] = {a**p} + {b**p} = {latex(result)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ D = \lim_{{{var} \to 0}} \dfrac{{\sin^{{{p}}}({a}{var}) + \sin^{{{p}}}({b}{var})}}{{{var}^{{{p}}}}} = {latex(result)} \]",
            None,
        ))
        return steps, checkpoints

    if formula == "limit:trig:sinc_rational_product":
        a = params.get("a", 3)
        b = params.get("b", 4)
        k = params.get("k", 6)
        c = params.get("c", 8)
        steps.append(_limit_step(
            "",
            rf"\[ E = \lim_{{{var} \to 0}} \dfrac{{\sin^3({a}{var})\sin^2({b}{var})}}{{{k}{var}^4\sin({c}{var})}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \dfrac{{1}}{{{k}}} \lim_{{{var} \to 0}} \left( \dfrac{{\sin^3({a}{var})}}{{{var}^3}} \times \dfrac{{\sin^2({b}{var})}}{{{var}^2}} \times \dfrac{{{var}}}{{\sin({c}{var})}} \right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \dfrac{{1}}{{{k}}} \lim_{{{var} \to 0}} \left[ \left(\dfrac{{\sin({a}{var})}}{{{a}{var}}} \times {a}\right)^3 \left(\dfrac{{\sin({b}{var})}}{{{b}{var}}} \times {b}\right)^2 \times \dfrac{{{c}{var}}}{{\sin({c}{var})}} \times \dfrac{{1}}{{{c}}} \right] = \dfrac{{{a}^3 \times {b}^2}}{{{k} \times {c}}} = {latex(result)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ E = \lim_{{{var} \to 0}} \dfrac{{\sin^3({a}{var})\sin^2({b}{var})}}{{{k}{var}^4\sin({c}{var})}} = {latex(result)} \]",
            None,
        ))
        return steps, checkpoints

    if formula == "limit:trig:half_angle_cubed":
        k = params.get("k", 2)
        half_var = rf"{k//2}{var}" if (k % 2 == 0 and k > 2) else (f"{var}" if k == 2 else rf"\dfrac{{{k}{var}}}{{2}}")
        half_sinc = rf"\left(\dfrac{{\sin {var}}}{{{var}}}\right)^2" if half_var == var else rf"\left(\dfrac{{\sin({half_var})}}{{{half_var}}} \times \dfrac{{{k}}}{{2}}\right)^2"
        steps.append(_limit_step(
            "",
            rf"\[ F = \lim_{{{var} \to 0}} \dfrac{{1 - \cos^3({k}{var})}}{{{var}^2}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{(1 - \cos({k}{var}))(1 + \cos({k}{var}) + \cos^2({k}{var}))}}{{{var}^2}} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{2\sin^2({half_var})(1 + \cos({k}{var}) + \cos^2({k}{var}))}}{{{var}^2}} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = 2\lim_{{{var} \to 0}} \left[ {half_sinc} (1 + \cos({k}{var}) + \cos^2({k}{var})) \right] = 2 \times 3 = {latex(result)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ F = \lim_{{{var} \to 0}} \dfrac{{1 - \cos^3({k}{var})}}{{{var}^2}} = {latex(result)} \]",
            None,
        ))
        return steps, checkpoints

    if formula == "limit:trig:cos_linear_combo":
        a = params.get("a", 2)
        b = params.get("b", 4)
        c1 = params.get("c1", 3)
        c2 = params.get("c2", 2)
        half_a = rf"{a//2}{var}" if (a % 2 == 0 and a > 2) else (f"{var}" if a == 2 else rf"\dfrac{{{a}{var}}}{{2}}")
        half_b = rf"{b//2}{var}" if (b % 2 == 0 and b > 2) else (f"{var}" if b == 2 else rf"\dfrac{{{b}{var}}}{{2}}")
        coeff_sin_a = 2 * c1
        coeff_sin_b = 2 * c2
        term_g_a = rf"{coeff_sin_a}\left(\dfrac{{\sin {var}}}{{{var}}}\right)^2" if half_a == var else rf"{coeff_sin_a}\left(\dfrac{{\sin({half_a})}}{{{half_a}}} \times \dfrac{{{a}}}{{2}}\right)^2"
        term_g_b = rf"{coeff_sin_b}\left(\dfrac{{\sin({half_b})}}{{{half_b}}} \times {b//2}\right)^2" if half_b != var else rf"{coeff_sin_b}\left(\dfrac{{\sin {var}}}{{{var}}}\right)^2"
        val_a = coeff_sin_a * (1 if half_a == var else (a // 2) ** 2)
        val_b = coeff_sin_b * ((b // 2) ** 2 if half_b != var else 1)
        steps.append(_limit_step(
            "",
            rf"\[ G = \lim_{{{var} \to 0}} \dfrac{{1 - {c1}\cos({a}{var}) + {c2}\cos({b}{var})}}{{{var}^2}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{{c1}(1 - \cos({a}{var})) - {c2}(1 - \cos({b}{var}))}}{{{var}^2}} = \lim_{{{var} \to 0}} \dfrac{{{coeff_sin_a}\sin^2({half_a}) - {coeff_sin_b}\sin^2({half_b})}}{{{var}^2}} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \left[ {term_g_a} - {term_g_b} \right] = {val_a} - {val_b} = {latex(result)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ G = \lim_{{{var} \to 0}} \dfrac{{1 - {c1}\cos({a}{var}) + {c2}\cos({b}{var})}}{{{var}^2}} = {latex(result)} \]",
            None,
        ))
        return steps, checkpoints

    if formula == "limit:trig:cos_sum_pair":
        a = params.get("a", 2)
        b = params.get("b", 4)
        half_a = rf"{a//2}{var}" if (a % 2 == 0 and a > 2) else (f"{var}" if a == 2 else rf"\dfrac{{{a}{var}}}{{2}}")
        half_b = rf"{b//2}{var}" if (b % 2 == 0 and b > 2) else (f"{var}" if b == 2 else rf"\dfrac{{{b}{var}}}{{2}}")
        term_h_a = rf"\left(\dfrac{{\sin {var}}}{{{var}}}\right)^2" if half_a == var else rf"\left(\dfrac{{\sin({half_a})}}{{{half_a}}} \times \dfrac{{{a}}}{{2}}\right)^2"
        term_h_b = rf"\left(\dfrac{{\sin({half_b})}}{{{half_b}}} \times {b//2}\right)^2"
        val_h_a = 1 if half_a == var else (a // 2) ** 2
        val_h_b = (b // 2) ** 2
        steps.append(_limit_step(
            "",
            rf"\[ H = \lim_{{{var} \to 0}} \dfrac{{2 - \cos({a}{var}) - \cos({b}{var})}}{{{var}^2}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{(1 - \cos({a}{var})) + (1 - \cos({b}{var}))}}{{{var}^2}} = \lim_{{{var} \to 0}} \dfrac{{2\sin^2({half_a}) + 2\sin^2({half_b})}}{{{var}^2}} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = 2\lim_{{{var} \to 0}} \left[ {term_h_a} + {term_h_b} \right] = 2({val_h_a} + {val_h_b}) = {latex(result)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ H = \lim_{{{var} \to 0}} \dfrac{{2 - \cos({a}{var}) - \cos({b}{var})}}{{{var}^2}} = {latex(result)} \]",
            None,
        ))
        return steps, checkpoints

    if formula == "limit:trig:tan_sin_combo":
        c = params.get("c", 2)
        a = params.get("a", 3)
        b = params.get("b", 1)
        coeff_tan = c * a
        steps.append(_limit_step(
            "",
            rf"\[ I = \lim_{{{var} \to 0}} \dfrac{{{c}\tan({a}{var}) - \sin({var})}}{{{var}}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \left( \dfrac{{{c}\tan({a}{var})}}{{{var}}} - \dfrac{{\sin({var})}}{{{var}}} \right) = \lim_{{{var} \to 0}} \left( {coeff_tan} \times \dfrac{{\tan({a}{var})}}{{{a}{var}}} - \dfrac{{\sin({var})}}{{{var}}} \right) = {coeff_tan} - 1 = {latex(result)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ I = \lim_{{{var} \to 0}} \dfrac{{{c}\tan({a}{var}) - \sin({var})}}{{{var}}} = {latex(result)} \]",
            None,
        ))
        return steps, checkpoints

    if formula == "limit:trig:tan_triple_angle":
        steps.append(_limit_step(
            "",
            rf"\[ J = \lim_{{{var} \to 0}} \dfrac{{3\tan {var} - \tan(3{var})}}{{{var}^3}} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{3\tan {var} - \dfrac{{3\tan {var} - \tan^3 {var}}}{{1 - 3\tan^2 {var}}}}}{{{var}^3}} = \lim_{{{var} \to 0}} \dfrac{{-8\tan^3 {var}}}{{{var}^3(1 - 3\tan^2 {var})}} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = -8\lim_{{{var} \to 0}} \dfrac{{\left(\dfrac{{\tan {var}}}{{{var}}}\right)^3}}{{1 - 3\tan^2 {var}}} = -8 \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ J = \lim_{{{var} \to 0}} \dfrac{{3\tan {var} - \tan(3{var})}}{{{var}^3}} = -8 \]",
            None,
        ))
        return steps, checkpoints

    return None



def _trig_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula):
    sakhon = _sakhon_trig_steps(formula, params, var, expr, result)
    if sakhon is not None:
        return sakhon

    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        )
    ]
    checkpoints = []

    # 1. Half-angle limit: (1 - cos(mx))/(bx^2) at x=0
    if (point == 0 or point == S.Zero) and expr.has(cos) and not expr.has(sin):
        cos_atoms = [at for at in expr.atoms(cos)]
        if cos_atoms:
            arg = cos_atoms[0].args[0]
            half_arg = arg / 2
            transformed = expr.subs(cos_atoms[0], 1 - 2*sin(half_arg)**2)
            steps.append(_limit_step(
                "",
                rf"\[ = {latex(transformed, ln_notation=True)} \]",
                None,
            ))
            steps.append(_limit_step(
                "",
                rf"\[ = {latex(result)} \cdot \left[\dfrac{{\sin\left({latex(half_arg)}\right)}}{{{latex(half_arg)}}}\right]^2 = {latex(result)} \]",
                None,
            ))
            steps.append(_limit_step(
                "",
                rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} = {latex(result)} \]",
                None,
            ))
            checkpoints.append({"label": "final value", "value": result, "formula": "direct_substitution"})
            return steps, checkpoints

    # 2. Ratio of sines or standard sinc at x=0
    if (point == 0 or point == S.Zero) and expr.has(sin) and not expr.has(cos):
        num, den = expr.as_numer_denom()
        steps.append(_limit_step(
            "",
            rf"\[ \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{\frac{{{latex(num)}}}{{{var}}}}}{{\frac{{{latex(den)}}}{{{var}}}}} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ = {latex(result)} \]",
            None,
        ))
        checkpoints.append({"label": "final value", "value": result, "formula": "limit_sin_x_over_x"})
        return steps, checkpoints

    # 3. Double-angle expansions: detect cos(2*w) in expr
    cos2_atoms = [at for at in expr.atoms(cos) if at.args[0] == 2*x or (isinstance(at.args[0], Rational) and at.args[0].p == 2)]
    if cos2_atoms:
        cos2_term = cos2_atoms[0]
        if expr.has(sin) and not (expr.has(cos) and len(expr.atoms(cos)) > 1):
            expanded_expr = expr.subs(cos2_term, 1 - 2*sin(x)**2)
        elif expr.has(cos) and len(expr.atoms(cos)) > 1 and not expr.has(sin):
            expanded_expr = expr.subs(cos2_term, 2*cos(x)**2 - 1)
        else:
            expanded_expr = expr.subs(cos2_term, cos(x)**2 - sin(x)**2)

        steps.append(_limit_step(
            "",
            rf"\[ = {latex(expanded_expr, ln_notation=True)} \]",
            None,
        ))
        cancelled = cancel(expanded_expr)
        if cancelled != expanded_expr:
            steps.append(_limit_step(
                "",
                rf"\[ = {latex(cancelled, ln_notation=True)} \]",
                None,
            ))
            steps.append(_limit_step(
                "",
                rf"\[ \lim_{{{var} \to {point_latex}}} {latex(cancelled, ln_notation=True)} = {latex(result)} \]",
                None,
            ))
            checkpoints.append({"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"})
            checkpoints.append({"label": "final value", "value": result, "formula": "direct_substitution"})
            return steps, checkpoints

    # 4. Pythagorean identity: detect cos^2(x) with 1 - sin(x) or sin^2(x) with 1 - cos(x)
    if expr.has(cos) and expr.has(sin):
        num, den = expr.as_numer_denom()
        if den.has(cos) and not den.has(sin) and num.has(sin):
            rewritten_den = den.subs(cos(x)**2, 1 - sin(x)**2)
            num_f = factor(num)
            steps.append(_limit_step(
                "",
                rf"\[ \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{{latex(num_f)}}}{{(1 - \sin {var})(1 + \sin {var})}} \]",
                None,
            ))
            checkpoints.append({"label": "factored form", "value": num_f / (1 - sin(x)**2), "formula": "trig_fundamental_relations"})
            cancelled = cancel(num / rewritten_den)
            if cancelled != expr:
                steps.append(_limit_step(
                    "",
                    rf"\[ = {latex(cancelled, ln_notation=True)} \]",
                    None,
                ))
                steps.append(_limit_step(
                    "",
                    rf"\[ \lim_{{{var} \to {point_latex}}} {latex(cancelled, ln_notation=True)} = {latex(result)} \]",
                    None,
                ))
                checkpoints.append({"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"})
                checkpoints.append({"label": "final value", "value": result, "formula": "direct_substitution"})
                return steps, checkpoints
        elif den.has(sin) and not den.has(cos) and num.has(cos):
            rewritten_den = den.subs(sin(x)**2, 1 - cos(x)**2)
            num_f = factor(num)
            steps.append(_limit_step(
                "",
                rf"\[ \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{{latex(num_f)}}}{{(1 - \cos {var})(1 + \cos {var})}} \]",
                None,
            ))
            checkpoints.append({"label": "factored form", "value": num_f / (1 - cos(x)**2), "formula": "trig_fundamental_relations"})
            cancelled = cancel(num / rewritten_den)
            if cancelled != expr:
                steps.append(_limit_step(
                    "",
                    rf"\[ = {latex(cancelled, ln_notation=True)} \]",
                    None,
                ))
                steps.append(_limit_step(
                    "",
                    rf"\[ \lim_{{{var} \to {point_latex}}} {latex(cancelled, ln_notation=True)} = {latex(result)} \]",
                    None,
                ))
                checkpoints.append({"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"})
                checkpoints.append({"label": "final value", "value": result, "formula": "direct_substitution"})
                return steps, checkpoints

    # 5. Change of variable at non-zero points (t = x - point or t = point - x)
    if point != 0 and point != S.Zero:
        num, den = expr.as_numer_denom()
        try:
            den_f = factor(den)
            if den_f != den:
                steps.append(_limit_step(
                    "",
                    rf"\[ = \lim_{{{var} \to {point_latex}}} \dfrac{{{latex(num)}}}{{{latex(den_f)}}} \]",
                    None,
                ))
        except Exception:
            pass

        t = Symbol("t")
        try:
            sub_expr = expr.subs(x, t + point)
            sub_expr_f = factor(sub_expr)
            steps.append(_limit_step(
                "",
                rf"\[ = \lim_{{t \to 0}} {latex(sub_expr_f, ln_notation=True)} \]",
                None,
            ))
        except Exception:
            pass

        steps.append(_limit_step(
            "",
            rf"\[ = {latex(result)} \]",
            None,
        ))
        steps.append(_limit_step(
            "",
            rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} = {latex(result)} \]",
            None,
        ))
        checkpoints.append({"label": "final value", "value": result, "formula": "limit_sin_x_over_x"})
        return steps, checkpoints

    # 6. Algebraic simplification of trig expressions
    try:
        simp = simplify(expr)
        if simp != expr and not simp.has(oo, -oo) and simp.subs(x, point).is_finite:
            steps.append(_limit_step(
                "",
                rf"\[ = {latex(simp, ln_notation=True)} \]",
                None,
            ))
            steps.append(_limit_step(
                "",
                rf"\[ \lim_{{{var} \to {point_latex}}} {latex(simp, ln_notation=True)} = {latex(result)} \]",
                None,
            ))
            checkpoints.append({"label": "simplified form", "value": simp, "formula": formula})
            checkpoints.append({"label": "final value", "value": result, "formula": "direct_substitution"})
            return steps, checkpoints
    except Exception:
        pass

    # Honest unclassified fallback
    steps.append(_limit_step(
        "",
        rf"\[ = {latex(result)} \]",
        None,
    ))
    checkpoints.append({"label": "final value", "value": result, "formula": "unclassified_valid"})
    return steps, checkpoints

    checkpoints.append({"label": "final value", "value": result, "formula": "unclassified_valid"})
    return steps, checkpoints


def _euler_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula):
    steps = []
    checkpoints = []

    steps.append(_limit_step(
        "",
        rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} \quad \left(\text{{រាងមិនកំណត់ }} 1^\infty\right) \]",
        None,
    ))

    base, pwr = expr.as_base_exp()
    u = simplify(base - 1)
    prod = pwr * u
    L = limit(prod, x, point)

    steps.append(_limit_step(
        "",
        rf"\[ f({var}) - 1 = {latex(base, ln_notation=True)} - 1 = {latex(u, ln_notation=True)} \]",
        None,
    ))
    checkpoints.append({"label": "base minus one", "value": u, "formula": "euler_base_minus_one"})

    # Check if the exponent limit requires trigonometric or algebraic transformation
    if prod.has(cos) and (point == 0 or point == S.Zero):
        cos_terms = [at for at in prod.atoms(cos)]
        if cos_terms:
            arg = cos_terms[0].args[0]
            half_arg = arg / 2
            sub_transformed = prod.subs(cos_terms[0], 1 - 2*sin(half_arg)**2)
            steps.append(_limit_step(
                "",
                rf"\[ g({var})(f({var}) - 1) = {latex(prod, ln_notation=True)} = {latex(sub_transformed, ln_notation=True)} \]",
                None,
            ))
            checkpoints.append({"label": "exponent transformed form", "value": sub_transformed, "formula": "trig_half_angle"})
            steps.append(_limit_step(
                "",
                rf"\[ L = \lim_{{{var} \to 0}} \left[{latex(sub_transformed, ln_notation=True)}\right] = {latex(L)} \]",
                None,
            ))
    elif prod.has(sin) and (point == 0 or point == S.Zero):
        steps.append(_limit_step(
            "",
            rf"\[ L = \lim_{{{var} \to 0}} g({var})(f({var}) - 1) = \lim_{{{var} \to 0}} \left({latex(pwr, ln_notation=True)} \cdot {latex(u, ln_notation=True)}\right) = {latex(L)} \]",
            None,
        ))
    else:
        steps.append(_limit_step(
            "",
            rf"\[ L = \lim_{{{var} \to {point_latex}}} g({var})(f({var}) - 1) = \lim_{{{var} \to {point_latex}}} \left({latex(pwr, ln_notation=True)} \cdot {latex(u, ln_notation=True)}\right) = {latex(L)} \]",
            None,
        ))

    checkpoints.append({"label": "exponent limit", "value": L, "formula": "euler_exponent_limit"})

    exp_L_latex = f"e^{{{latex(L)}}}"
    res_latex = latex(result)
    conclusion_eq = f"{exp_L_latex} = {res_latex}" if exp_L_latex != res_latex else exp_L_latex
    steps.append(_limit_step(
        "",
        rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} = {conclusion_eq} \]",
        None,
    ))

    checkpoints.append({"label": "final value", "value": result, "formula": "euler_final_exp"})

    return steps, checkpoints


def _infinity_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula):
    if _has_radical(expr):
        return _handle_conjugate_infinity(params, var, x, point, point_latex, expr, result)
    else:
        return _handle_rational_function_infinity(params, var, x, point, point_latex, expr, result)



def _exponential_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula):
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        )
    ]
    checkpoints = []
    if point == 0 or point == S.Zero:
        steps.append(_limit_step(
            "",
            rf"\[ = {latex(expr, ln_notation=True)} \]",
            None,
        ))
        cps = _exponential_standard_limit_checkpoints(x, point, expr, formula)
        checkpoints.extend(cps)
    steps.append(_limit_step(
        "",
        rf"\[ = {latex(result)} \]",
        None,
    ))
    checkpoints.append({"label": "final value", "value": result, "formula": formula})
    return steps, checkpoints


def _logarithmic_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula):
    tag = r"\dfrac{0}{0}" if (point == 0 or point == S.Zero) else r"\dfrac{\infty}{\infty}"
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} \quad \left(\text{{រាងមិនកំណត់ }} {tag}\right) \]",
            None,
        )
    ]
    checkpoints = []
    steps.append(_limit_step(
        "",
        rf"\[ = {latex(expr, ln_notation=True)} \]",
        None,
    ))
    cps = _logarithmic_standard_limit_checkpoints(x, point, expr, formula)
    checkpoints.extend(cps)
    steps.append(_limit_step(
        "",
        rf"\[ = {latex(result)} \]",
        None,
    ))
    checkpoints.append({"label": "final value", "value": result, "formula": formula})
    return steps, checkpoints


def _curated_limit_steps(params, var, x, point, point_latex, expr, result):
    """Generic ``formula_name``-keyed step deriver, used for every procedurally
    sampled limit structure (params["formula_name"] is set by the structure's
    own catalogue entry, not by a per-exercise author). SymPy still computes
    `result` (the graded answer); the technique's own narration text
    (``_derived_technique_text`` or an authored ``curated_technique``/title)
    describes the steps instead of a fully bespoke technique handler. A
    handful of formula_names still get a generically-derived intermediate
    checkpoint (either by reusing the parameter-free handler for the same
    technique, or a bespoke generic deriver for
    `rationalization_conjugate_finite`) so correct intermediate work verifies
    instead of only the final answer."""
    formula = params["formula_name"]

    from .blueprint_interpreter import interpret_blueprint_steps
    bp_steps, bp_cps = interpret_blueprint_steps(formula, params, var, point, point_latex, expr, result)
    if bp_steps:
        return bp_steps, bp_cps

    if formula in _ONE_SIDED_RADICAL_KINDS:
        steps, reduced = _one_sided_radical_steps(
            _ONE_SIDED_RADICAL_KINDS[formula], params, var, x, point_latex, expr, result,
        )
        return steps, [
            {"label": "simplified form", "value": reduced, "formula": formula},
            {"label": "final value", "value": result, "formula": formula},
        ]

    if formula.startswith("limit:rational:"):
        rat_res = _rational_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula)
        if rat_res is not None:
            return rat_res

    if formula.startswith("limit:radical:"):
        rad_res = _radical_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula)
        if rad_res is not None:
            return rad_res

    if formula.startswith("limit:trig:") or formula in ("sinc_standard_limit", "half_angle_sinc_combo"):
        trig_res = _trig_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula)
        if trig_res is not None:
            return trig_res

    if formula.startswith("limit:exponential:") or formula in ("exponential_standard_limit", "exponential_sinc_combo"):
        exp_res = _exponential_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula)
        if exp_res is not None:
            return exp_res

    if formula.startswith("limit:euler:") or formula in ("indeterminate_one_infinity", "EU1", "EU2") or "one_inf" in formula or "euler" in formula:
        euler_res = _euler_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula)
        if euler_res is not None:
            return euler_res

    if formula.startswith("limit:infinity:") or formula in ("conjugate_infinity", "INF1", "INF2"):
        inf_res = _infinity_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula)
        if inf_res is not None:
            return inf_res

    if formula.startswith("limit:logarithmic:") or formula.startswith("limit:log") or formula in ("log_limit_zero", "log_limit_infinity"):
        log_res = _logarithmic_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula)
        if log_res is not None:
            return log_res

    tag = r"\dfrac{0}{0}"
    if point in (oo, -oo):
        tag = r"\dfrac{\infty}{\infty}"
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} \quad \left(\text{{រាងមិនកំណត់ }} {tag}\right) \]",
            None,
        )
    ]
    try:
        simp = cancel(expr)
        if simp != expr and not _has_huge_power(expr):
            steps.append(_limit_step("", rf"\[ = \lim_{{{var} \to {point_latex}}} {latex(simp, ln_notation=True)} \]", None))
    except Exception:
        pass
    steps.append(_limit_step("", rf"\[ = {latex(result)} \]", None))
    checkpoints = []
    if formula == "rationalization_conjugate_finite" or formula.startswith("limit:radical:"):
        checkpoints.extend(_rationalization_conjugate_checkpoints(x, point, expr, formula))
    elif formula in ("exponential_standard_limit", "E1", "E2", "E3") or formula.startswith("limit:exponential"):
        checkpoints.extend(_exponential_standard_limit_checkpoints(x, point, expr, formula))
    elif formula in ("indeterminate_one_infinity", "EU1", "EU2") or "one_inf" in formula or "euler" in formula:
        checkpoints.extend(_one_infinity_checkpoints(x, point, expr, formula))
    elif formula in ("log_limit_zero", "log_limit_infinity", "L1", "L2", "L3", "L4") or formula.startswith("limit:logarithmic") or formula.startswith("limit:log"):
        checkpoints.extend(_logarithmic_standard_limit_checkpoints(x, point, expr, formula))
    elif formula in _CURATED_REUSABLE_HANDLERS:
        try:
            _, extra_cps = _LIMIT_TECHNIQUE_HANDLERS[formula]({}, var, x, point, point_latex, expr, result)
            for cp in extra_cps:
                if simplify(cp["value"] - result) != 0:
                    checkpoints.append({**cp, "formula": formula})
        except Exception:
            pass
    checkpoints.append({"label": "final value", "value": result, "formula": formula})
    return steps, checkpoints


def _handle_direct_substitution(params, var, x, point, point_latex, expr, result):
    direct = simplify(expr.subs(x, point))
    steps = [_limit_step(
        "",
        rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr)} = {latex(direct)} \]",
        None,
    )]
    checkpoints = [{"label": "substituted value", "value": direct, "formula": "direct_substitution"}]
    return steps, checkpoints


def _handle_factoring_0_0(params, var, x, point, point_latex, expr, result):
    num, den = expr.as_numer_denom()
    deg_num = degree(num, x) if (hasattr(num, "is_polynomial") and num.is_polynomial(x)) else 1
    deg_den = degree(den, x) if (hasattr(den, "is_polynomial") and den.is_polynomial(x)) else 1
    if deg_num > 6 or deg_den > 6:
        rat_res = _rational_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, "limit_power_identity")
        if rat_res is not None:
            return rat_res
    num_f = factor(num)
    den_f = factor(den)
    cancelled = cancel(num_f / den_f)
    sub_val = simplify(cancelled.subs(x, point))
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to {point_latex}}} \dfrac{{{latex(num_f)}}}{{{latex(den_f)}}} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to {point_latex}}} {latex(cancelled)} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {latex(sub_val)} \]",
            None,
        ),
    ]
    checkpoints = [
        {"label": "factored form", "value": num_f / den_f, "formula": "factor_difference_of_squares"},
        {"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"},
        {"label": "substituted value", "value": sub_val, "formula": "direct_substitution"},
    ]
    return steps, checkpoints


def _handle_rational_function_infinity(params, var, x, point, point_latex, expr, result):
    num, den = expr.as_numer_denom()
    n = max(degree(num, x), degree(den, x))
    divided = expand(num / x**n) / expand(den / x**n)
    ratio = limit(divided, x, oo)
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to \infty}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{\infty}}{{\infty}}\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to \infty}} {latex(divided)} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {latex(ratio)} \]",
            None,
        ),
    ]
    checkpoints = [
        {"label": "divided by highest power", "value": divided, "formula": "divide_highest_power"},
        {"label": "leading coefficient ratio", "value": ratio, "formula": "leading_coefficient_ratio"},
    ]
    return steps, checkpoints


def _handle_sinc_standard_limit(params, var, x, point, point_latex, expr, result):
    k, c = params["k"], params.get("c", 1)
    kx = f"{k}{var}" if k != 1 else var
    coeff_prefix = f"{c} \\cdot " if c != 1 else ""
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to 0}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {coeff_prefix}{k} \lim_{{{var} \to 0}} \dfrac{{\sin({kx})}}{{{kx}}} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {latex(result)} \]",
            None,
        ),
    ]
    rewritten = c * k * sin(k * x) / (k * x)
    checkpoints = [
        {"label": "rewritten form", "value": rewritten, "formula": "sinc_standard_limit"},
        {"label": "final value", "value": result, "formula": "sinc_standard_limit"},
    ]
    return steps, checkpoints


def _handle_exponential_standard_limit(params, var, x, point, point_latex, expr, result):
    a, b = params["a"], params["b"]
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to 0}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{\frac{{e^{{{a}{var}}}-1}}{{{var}}}}}{{\frac{{e^{{{b}{var}}}-1}}{{{var}}}}} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \dfrac{{{a}}}{{{b}}} = {latex(result)} \]",
            None,
        ),
    ]
    checkpoints = _exponential_standard_limit_checkpoints(x, point, expr, "exponential_standard_limit")
    checkpoints.append({"label": "final value", "value": result, "formula": "exponential_standard_limit"})
    return steps, checkpoints


def _handle_conjugate_infinity(params, var, x, point, point_latex, expr, result):
    k, b, c, d = params["k"], params["b"], params["c"], params["d"]
    sqrt_part = sqrt(k**2 * x**2 + b * x + c)
    linear_part = k * x + d
    conjugate = sqrt_part + linear_part
    numerator = expand(sqrt_part**2 - linear_part**2)
    divided = expand(numerator / x) / expand(conjugate / x)
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to \infty}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \infty - \infty\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to \infty}} \dfrac{{{latex(numerator)}}}{{{latex(conjugate)}}} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to \infty}} {latex(divided)} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {latex(result)} \]",
            None,
        ),
    ]
    checkpoints = [
        {"label": "divided by highest power", "value": divided, "formula": "divide_highest_power"},
        {"label": "final value", "value": result, "formula": "leading_coefficient_ratio"},
    ]
    return steps, checkpoints


def _handle_rationalization_conjugate_finite(params, var, x, point, point_latex, expr, result):
    p, d, c, n = params["p"], params["d"], params["c"], params["n"]
    conjugate = sqrt(x + c) + d
    numerator_poly = expand(x**n - p**n)
    poly_ratio = cancel(numerator_poly / (x - p))
    cancelled = expand(poly_ratio) * conjugate
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to {point_latex}}} \dfrac{{{latex(numerator_poly)} \cdot ({latex(conjugate)})}}{{{var}-{p}}} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to {point_latex}}} {latex(cancelled)} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {latex(result)} \]",
            None,
        ),
    ]
    checkpoints = [
        {"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"},
        {"label": "final value", "value": result, "formula": "direct_substitution"},
    ]
    return steps, checkpoints


def _handle_rationalization_sinc_combo(params, var, x, point, point_latex, expr, result):
    a, k = params["a"], params["k"]
    conjugate = sqrt(a + x) + sqrt(a - x)
    part1 = limit(2 * x / sin(k * x), x, 0)
    part2 = limit(1 / conjugate, x, 0)
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to 0}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{2{var}}}{{\sin({k}{var}) \cdot ({latex(conjugate)})}} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{2{var}}}{{\sin({k}{var})}} \times \lim_{{{var} \to 0}} \dfrac{{1}}{{{latex(conjugate)}}} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {latex(result)} \]",
            None,
        ),
    ]
    checkpoints = [
        {"label": "sinc factor", "value": part1, "formula": "rationalization_sinc_combo"},
        {"label": "conjugate factor", "value": part2, "formula": "rationalization_sinc_combo"},
        {"label": "final value", "value": result, "formula": "rationalization_sinc_combo"},
    ]
    return steps, checkpoints


def _handle_exponential_sinc_combo(params, var, x, point, point_latex, expr, result):
    a, k = params["a"], params["k"]
    continuous_val = (exp(a * x) + exp(-a * x)).subs(x, 0)
    sinc_sq = limit(sin(k * x)**2 / x**2, x, 0)
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to 0}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{(e^{{{a}{var}}}+e^{{-{a}{var}}})}}{{2}} \times \lim_{{{var} \to 0}} \dfrac{{\sin^2({k}{var})}}{{{var}^2}} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {latex(result)} \]",
            None,
        ),
    ]
    checkpoints = [
        {"label": "exponential factor", "value": continuous_val, "formula": "exponential_sinc_combo"},
        {"label": "sinc-squared factor", "value": sinc_sq, "formula": "exponential_sinc_combo"},
        {"label": "final value", "value": result, "formula": "exponential_sinc_combo"},
    ]
    return steps, checkpoints


def _handle_half_angle_sinc_combo(params, var, x, point, point_latex, expr, result):
    k, m = params["k"], params["m"]
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to 0}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \dfrac{{0}}{{0}}\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = \lim_{{{var} \to 0}} \dfrac{{\sin({k}{var})}}{{{var}}} \times \lim_{{{var} \to 0}} \dfrac{{1-\\cos({m}{var})}}{{{var}^2}} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {latex(result)} \]",
            None,
        ),
    ]
    part1 = limit(sin(k * x) / x, x, 0)
    part2 = limit((1 - cos(m * x)) / x**2, x, 0)
    checkpoints = [
        {"label": "sinc factor", "value": part1, "formula": "half_angle_sinc_combo"},
        {"label": "half-angle factor", "value": part2, "formula": "half_angle_sinc_combo"},
        {"label": "final value", "value": result, "formula": "half_angle_sinc_combo"},
    ]
    return steps, checkpoints


def _handle_log_limit_infinity(params, var, x, point, point_latex, expr, result):
    c, k = params["c"], params["k"]
    coeff_prefix = f"{c} \\cdot " if c != 1 else ""
    steps = [
        _limit_step(
            "",
            rf"\[ \lim_{{{var} \to \infty}} {latex(expr)} \quad \left(\text{{រាងមិនកំណត់ }} \infty \times 0\right) \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {coeff_prefix}{k} \lim_{{{var} \to \infty}} \dfrac{{\ln(1 + \frac{{{k}}}{{{var}}})}}{{\frac{{{k}}}{{{var}}}}} \]",
            None,
        ),
        _limit_step(
            "",
            rf"\[ = {latex(result)} \]",
            None,
        ),
    ]
    rewritten = c * x * log(1 + k / x)
    checkpoints = [
        {"label": "rewritten form", "value": rewritten, "formula": "log_limit_infinity"},
        {"label": "final value", "value": result, "formula": "log_limit_infinity"},
    ]
    return steps, checkpoints



_LIMIT_TECHNIQUE_HANDLERS = {
    "direct_substitution": _handle_direct_substitution,
    "factoring_0_0": _handle_factoring_0_0,
    "rational_function_infinity": _handle_rational_function_infinity,
    "sinc_standard_limit": _handle_sinc_standard_limit,
    "exponential_standard_limit": _handle_exponential_standard_limit,
    "conjugate_infinity": _handle_conjugate_infinity,
    "rationalization_conjugate_finite": _handle_rationalization_conjugate_finite,
    "rationalization_sinc_combo": _handle_rationalization_sinc_combo,
    "exponential_sinc_combo": _handle_exponential_sinc_combo,
    "half_angle_sinc_combo": _handle_half_angle_sinc_combo,
    "log_limit_infinity": _handle_log_limit_infinity,
}


def _legacy_inferred_steps(var, x, point, point_latex, expr, result):
    """Fallback classification for limit params with neither `formula_name` nor
    a known `technique` (shouldn't happen once callers always tag one of
    those, but kept as a safety net)."""
    if point in (oo, -oo):
        try:
            return _handle_rational_function_infinity({}, var, x, point, point_latex, expr, result)
        except Exception:
            return [
                _limit_step("", rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr)} = {latex(result)} \]", None)
            ], [{"label": "final value", "value": result, "formula": "direct_substitution"}]
    try:
        direct = simplify(expr.subs(x, point))
    except Exception:
        direct = None
    if direct is not None and direct.is_finite:
        return _handle_direct_substitution({}, var, x, point, point_latex, expr, result)
    return _handle_factoring_0_0({}, var, x, point, point_latex, expr, result)



def _solve_limit(params):
    var = params["var"]
    x = Symbol(var)
    expr = sympify(params["expr"], locals=_calc_locals(var))
    point = sympify(params["point"], locals=_calc_locals(var))
    side = params.get("side")
    kwargs = {"dir": side} if side else {}
    num, den = expr.as_numer_denom()
    is_poly_num = hasattr(num, "is_polynomial") and num.is_polynomial(x)
    is_poly_den = hasattr(den, "is_polynomial") and den.is_polynomial(x)
    if is_poly_num and is_poly_den and point not in (oo, -oo):
        deg_n = degree(num, x)
        deg_d = degree(den, x)
        if (deg_n > 6 or deg_d > 6) and num.subs(x, point) == 0 and den.subs(x, point) == 0:
            result = diff(num, x).subs(x, point) / diff(den, x).subs(x, point)
        else:
            result = limit(expr, x, point, **kwargs)
    else:
        result = limit(expr, x, point, **kwargs)

    point_latex = latex(point) + ("^" + ("+" if side == "+" else "-") if side else "")

    formula_name = params.get("formula_name") or params.get("structure_id")
    if formula_name:
        params["formula_name"] = formula_name
        more_steps, checkpoints = _curated_limit_steps(params, var, x, point, point_latex, expr, result)
    else:
        technique = params.get("technique")
        handler = _LIMIT_TECHNIQUE_HANDLERS.get(technique)
        if handler:
            more_steps, checkpoints = handler(params, var, x, point, point_latex, expr, result)
        else:
            more_steps, checkpoints = _legacy_inferred_steps(var, x, point, point_latex, expr, result)

    if more_steps:
        steps = more_steps
    else:
        steps = [
            _limit_step(
                "",
                rf"\[ \lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} = {latex(result)} \]",
                None,
            ),
        ]


    try:
        decimal = float(N(result, 8))
    except TypeError:
        decimal = str(result)
    return {
        "answer_exact": result,
        "answer_decimal": decimal,
        "answer_latex": latex(result),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
        "given": expr,
        "point": point,
        "var": var,
    }