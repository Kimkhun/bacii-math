"""Limit solver (technique handlers for parameterizable techniques + curated ``formula_name`` branch)."""
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
    return {"title": title, "detail": detail, "formula": formula}


def _has_radical(e):
    return any(isinstance(a, Pow) and not a.exp.is_integer for a in e.atoms(Pow))


def _rationalization_conjugate_checkpoints(x, point, expr, formula):
    """Derive the intermediate "cancelled form" checkpoint for a 0/0 limit
    where exactly one of numerator/denominator carries a square root: rationalize
    that side by its conjugate, cancel the shared (x - point) factor against the
    other (polynomial) side, and report the resulting expression. Generalizes the
    5 curated `rationalization_conjugate_finite` exercises (whichever side —
    numerator or denominator — the sqrt is on, and any leading constant
    multiplier) instead of hardcoding each one. Returns [] when the shape
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
# purely from (x, point, expr) — no technique-specific params like a curated
# exercise's k/a/d — so it can be reused as-is to derive intermediate
# checkpoints for the curated version of the same technique.
_CURATED_REUSABLE_HANDLERS = {"direct_substitution", "factoring_0_0", "rational_function_infinity"}


def _exponential_standard_limit_checkpoints(x, point, expr, formula):
    """Derive the two intermediate "divide by the variable, apply the
    standard exponential limit separately" checkpoints for a 0/0 limit shaped
    like (e^{ax}-1)/(e^{bx}-1) at x=0: the numerator and denominator each
    divided by x and limited on their own (giving a and b respectively).
    Purely generic on `expr` — no a/b params needed — so it covers curated
    exercises too, whatever the exact coefficients. Returns [] when the
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
    """Narration + checkpoint for the two sqrt(trig)/sin limits at pi^-: the
    radical only simplifies once the sign of sin (or cos of the half angle) on
    the left of pi is spelled out, which is why the side matters."""
    k = params.get("k", 1)
    kpre = f"{k}" if k != 1 else ""
    if kind == "half":
        reduced = k * sqrt(2) / (2 * sin(x / 2))
        steps = [
            _limit_step(
                "Rewrite with half-angle identities",
                f"\\(1 + \\cos {var} = 2\\cos^2\\tfrac{{{var}}}{{2}}\\) and \\(\\sin {var} = 2\\sin\\tfrac{{{var}}}{{2}}\\cos\\tfrac{{{var}}}{{2}}\\).",
                "half_angle_identity",
            ),
            _limit_step(
                "Take the square root using the side",
                f"For \\({var} \\to \\pi^-\\) we have \\(\\tfrac{{{var}}}{{2}} < \\tfrac{{\\pi}}{{2}}\\), so \\(\\cos\\tfrac{{{var}}}{{2}} > 0\\) and "
                f"\\(\\sqrt{{1 + \\cos {var}}} = \\sqrt{{2}}\\cos\\tfrac{{{var}}}{{2}}\\) (no absolute value needed).",
                "one_sided_sign",
            ),
            _limit_step(
                "Cancel and substitute",
                f"The expression becomes \\({kpre}\\dfrac{{\\sqrt{{2}}}}{{2\\sin\\tfrac{{{var}}}{{2}}}}\\), which tends to {inline_latex(result)} as \\({var} \\to \\pi^-\\).",
                "one_sided_sign",
            ),
        ]
    else:
        reduced = k * sqrt(2) / (2 * cos(x))
        steps = [
            _limit_step(
                "Rewrite with double-angle identities",
                f"\\(1 - \\cos 2{var} = 2\\sin^2 {var}\\) and \\(\\sin 2{var} = 2\\sin {var}\\cos {var}\\).",
                "double_angle_identity",
            ),
            _limit_step(
                "Take the square root using the side",
                f"For \\({var} \\to \\pi^-\\) we have \\(\\sin {var} > 0\\), so \\(\\sqrt{{2\\sin^2 {var}}} = \\sqrt{{2}}\\sin {var}\\). "
                f"From the right of \\(\\pi\\) it would be \\(-\\sqrt{{2}}\\sin {var}\\), so the two sides give opposite signs and the side must be stated.",
                "one_sided_sign",
            ),
            _limit_step(
                "Cancel and substitute",
                f"The expression becomes \\({kpre}\\dfrac{{\\sqrt{{2}}}}{{2\\cos {var}}}\\), which tends to {inline_latex(result)} as \\({var} \\to \\pi^-\\).",
                "one_sided_sign",
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
    from technique templates rather than the curated exam JSON): the technique's
    catalogue name plus, when SymPy can simplify the expression, that simplification.
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
                    "Verify indeterminate form 0/0 (ផ្ទៀងផ្ទាត់រាងមិនកំណត់ 0/0)",
                    rf"Substituting \({var} = {point_latex}\) into numerator and denominator gives \(\dfrac{{0}}{{0}}\), an indeterminate form.",
                    "setup_limit",
                ),
                _limit_step(
                    "Divide numerator and denominator by (x - a) (ចែកភាគយកនិងភាគបែងនឹង x - a)",
                    rf"Use the Bac II power limit identity \(\lim_{{{var} \to {point_latex}}} \dfrac{{{var}^n - ({point_latex})^n}}{{{var} - ({point_latex})}} = n({point_latex})^{{n-1}}\):"
                    rf"\[ \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{\frac{{{latex(num)}}}{{{var} - ({point_latex})}}}}{{\frac{{{latex(den)}}}{{{var} - ({point_latex})}}}} \]",
                    "limit_power_identity",
                ),
            ]
            d_num = diff(num, x)
            d_den = diff(den, x)
            val_num = d_num.subs(x, point)
            val_den = d_den.subs(x, point)
            steps.append(_limit_step(
                "Evaluate numerator and denominator limits independently (គណនាលីមីតភាគយកនិងភាគបែង)",
                rf"Calculate each derivative limit:"
                rf"\[ \lim_{{{var} \to {point_latex}}} \dfrac{{{latex(num)}}}{{{var} - ({point_latex})}} = {latex(val_num)}, \quad "
                rf"\lim_{{{var} \to {point_latex}}} \dfrac{{{latex(den)}}}{{{var} - ({point_latex})}} = {latex(val_den)} \]",
                "limit_power_identity",
            ))
            steps.append(_limit_step(
                "Compute the quotient of limits (គណនាតម្លៃចុងក្រោយ)",
                rf"Therefore, \(\lim_{{{var} \to {point_latex}}} \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{{latex(val_num)}}}{{{latex(val_den)}}} = {latex(result)}\).",
                "limit_power_identity",
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
                "Try direct substitution (ជំនួសតម្លៃផ្ទាល់)",
                rf"Substituting \({var} = {point_latex}\) gives \(0/0\), an indeterminate form, so we factor and simplify.",
                "setup_limit",
            ),
        ]
        checkpoints = []

        try:
            num_f = factor(num)
            den_f = factor(den)
            steps.append(_limit_step(
                "Factor numerator and denominator (ដាក់ជាផលគុណកត្តា)",
                rf"\[ {latex(expr)} = \dfrac{{{latex(num_f)}}}{{{latex(den_f)}}} \]",
                formula,
            ))
            checkpoints.append({"label": "factored form", "value": num_f / den_f, "formula": formula})
        except Exception:
            pass

        steps.append(_limit_step(
            "Cancel common vanishing factor (សម្រួលកត្តារួម)",
            rf"Cancel the vanishing factor to simplify:"
            rf"\[ = {latex(cancelled)} \]",
            "cancel_common_factor",
        ))
        steps.append(_limit_step(
            "Evaluate by direct substitution (ជំនួសតម្លៃផ្ទាល់)",
            rf"Substitute \({var} = {point_latex}\):"
            rf"\[ \lim_{{{var} \to {point_latex}}} {latex(cancelled)} = {latex(sub_val)} \]",
            "direct_substitution",
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
                    "Try direct substitution",
                    rf"Substituting \({var} = {point_latex}\) gives \(0/0\), an indeterminate form.",
                    "setup_limit",
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
                "Separate into partial limits by adding and subtracting constants",
                rf"Split into independent rationalizable fractions:"
                rf"\[ {latex(expr)} = {' + '.join(branch_strs)} \]",
                "rationalization_conjugate_finite",
            ))
            steps.append(_limit_step(
                "Multiply each fraction by its conjugate factor",
                rf"Multiply each branch by its corresponding conjugate (for square root: \(\sqrt{{A}}+B\); for cube root: \(A^{{2/3}} + A^{{1/3}}B + B^2\)).",
                "rationalization_conjugate_finite",
            ))
            steps.append(_limit_step(
                "Cancel the common vanishing factor and evaluate each branch",
                rf"Cancelling the vanishing factor \({var} - {point_latex}\) gives partial limits: "
                + " and ".join(rf"\({latex(val)}\)" for val in sub_limits) + ".",
                "cancel_common_factor",
            ))
            steps.append(_limit_step(
                "Sum partial limits to obtain final result",
                rf"The total limit is \({' + '.join(latex(val) for val in sub_limits)} = {latex(result)}\).",
                "direct_substitution",
            ))
            checkpoints = [{"label": "final value", "value": result, "formula": formula}]
            return steps, checkpoints

        # Check for cube root single radical: A^(1/3) - B
        cbrt_atoms = [a for a in expr.atoms(Pow) if a.exp == Rational(1, 3)]
        if cbrt_atoms:
            steps = [
                _limit_step(
                    "Try direct substitution",
                    rf"Substituting \({var} = {point_latex}\) gives \(0/0\), an indeterminate form.",
                    "setup_limit",
                ),
                _limit_step(
                    "Apply difference of cubes identity (រូបមន្តផលដកគូប)",
                    rf"Use the identity \(a - b = \dfrac{{a^3 - b^3}}{{a^2 + ab + b^2}}\) by multiplying numerator and denominator by the quadratic conjugate factor.",
                    "rationalization_conjugate_finite",
                ),
                _limit_step(
                    "Cancel the common vanishing factor",
                    rf"Cancel the vanishing factor \({var} - {point_latex}\) between numerator and denominator.",
                    "cancel_common_factor",
                ),
                _limit_step(
                    "Evaluate by direct substitution",
                    rf"Substitute \({var} = {point_latex}\): the limit evaluates to \({latex(result)}\).",
                    "direct_substitution",
                )
            ]
            checkpoints = [{"label": "final value", "value": result, "formula": formula}]
            return steps, checkpoints

        # Check for ratio of powers / nth roots at 1
        if point == 1 and expr.has(Pow):
            steps = [
                _limit_step(
                    "Try direct substitution",
                    rf"Substituting \({var} = 1\) gives \(0/0\), an indeterminate form.",
                    "setup_limit",
                ),
                _limit_step(
                    "Divide numerator and denominator by the variable difference",
                    rf"Divide numerator and denominator by \({var} - 1\) to recognize standard derivative / limit forms:"
                    rf"\[ \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{\frac{{{latex(num)}}}{{{var} - 1}}}}{{\frac{{{latex(den)}}}{{{var} - 1}}}} \]",
                    "rationalization_conjugate_finite",
                ),
                _limit_step(
                    "Evaluate limit of numerator and denominator",
                    rf"Since \(\lim_{{{var} \to 1}} \dfrac{{{var}^p - 1}}{{{var} - 1}} = p\), the ratio evaluates to \({latex(result)}\).",
                    "direct_substitution",
                )
            ]
            checkpoints = [{"label": "final value", "value": result, "formula": formula}]
            return steps, checkpoints

        # Check standard square-root conjugate checkpoints
        cps = _rationalization_conjugate_checkpoints(x, point, expr, formula)
        if cps:
            cancelled = cps[0]["value"]
            steps = [
                _limit_step(
                    "Multiply and divide by the conjugate",
                    f"Direct substitution gives \\(0/0\\). Multiply the numerator and denominator by the conjugate.",
                    formula,
                ),
                _limit_step(
                    "Simplify and cancel the common factor",
                    f"After expanding the conjugate and cancelling, the expression becomes {inline_latex(cancelled)}.",
                    formula,
                ),
                _limit_step(
                    "Evaluate by direct substitution",
                    f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(cancelled)}\\) = {inline_latex(result)}.",
                    formula,
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
            "Multiply by conjugate expression (គុណនឹងកន្សោមឆ្លាស់)",
            rf"Multiply numerator and denominator by the conjugate expression to rationalize the indeterminate form \(0/0\):"
            rf"\[ {latex(expr, ln_notation=True)} \]",
            "rationalization_conjugate_finite",
        ),
        _limit_step(
            "Cancel common vanishing factor and evaluate",
            rf"Cancel the common factor and evaluate as \({var} \to {point_latex}\) to obtain \({latex(result)}\).",
            "direct_substitution",
        )
    ]
    checkpoints = [{"label": "final value", "value": result, "formula": formula}]
    return steps, checkpoints


def _trig_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula):
    steps = [
        _limit_step(
            "Try direct substitution",
            f"Substituting \\({var} = {point_latex}\\) gives \\(0/0\\), an indeterminate form, so we use trigonometric identities.",
            "direct_substitution",
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
                "Apply half-angle formula (រូបមន្តកន្លះមុំ)",
                rf"Use \(1 - \cos({latex(arg)}) = 2\sin^2\left({latex(half_arg)}\right)\):"
                rf"\[ {latex(expr, ln_notation=True)} = {latex(transformed, ln_notation=True)} \]",
                "trig_half_angle",
            ))
            checkpoints.append({"label": "half-angle transformed form", "value": transformed, "formula": "trig_half_angle"})
            steps.append(_limit_step(
                "Normalize to fundamental limit (រូបមន្តលីមីតត្រីកោណមាត្រគ្រឹះ)",
                rf"Reorganize into the standard form \(\lim_{{u \to 0}} \dfrac{{\sin u}}{{u}} = 1\):"
                rf"\[ = {latex(result)} \cdot \left[\dfrac{{\sin\left({latex(half_arg)}\right)}}{{{latex(half_arg)}}}\right]^2 \]",
                "limit_sin_x_over_x",
            ))
            steps.append(_limit_step(
                "Evaluate limit (គណនាតម្លៃចុងក្រោយ)",
                rf"Since \(\lim_{{{var} \to 0}} \dfrac{{\sin({latex(half_arg)})}}{{{latex(half_arg)}}} = 1\), the limit is \({latex(result)}\).",
                "direct_substitution",
            ))
            checkpoints.append({"label": "final value", "value": result, "formula": "direct_substitution"})
            return steps, checkpoints

    # 2. Ratio of sines or standard sinc at x=0
    if (point == 0 or point == S.Zero) and expr.has(sin) and not expr.has(cos):
        num, den = expr.as_numer_denom()
        steps.append(_limit_step(
            "Divide by the variable to isolate fundamental trigonometric limits",
            rf"Divide numerator and denominator by \({var}\) to apply \(\lim_{{u \to 0}} \dfrac{{\sin u}}{{u}} = 1\):"
            rf"\[ \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{\frac{{{latex(num)}}}{{{var}}}}}{{\frac{{{latex(den)}}}{{{var}}}}} \]",
            "limit_sin_x_over_x",
        ))
        steps.append(_limit_step(
            "Apply fundamental trigonometric limit (រូបមន្តលីមីតត្រីកោណមាត្រគ្រឹះ)",
            rf"Since \(\lim_{{u \to 0}} \dfrac{{\sin u}}{{u}} = 1\), evaluating each factor yields \({latex(result)}\).",
            "limit_sin_x_over_x",
        ))
        checkpoints.append({"label": "final value", "value": result, "formula": "limit_sin_x_over_x"})
        return steps, checkpoints

    # 3. Double-angle expansions: detect cos(2*w) in expr
    cos2_atoms = [at for at in expr.atoms(cos) if at.args[0] == 2*x or (isinstance(at.args[0], Rational) and at.args[0].p == 2)]
    if cos2_atoms:
        cos2_term = cos2_atoms[0]
        if expr.has(sin) and not (expr.has(cos) and len(expr.atoms(cos)) > 1):
            identity_latex = rf"\cos(2{var}) = 1 - 2\sin^2({var})"
            expanded_expr = expr.subs(cos2_term, 1 - 2*sin(x)**2)
        elif expr.has(cos) and len(expr.atoms(cos)) > 1 and not expr.has(sin):
            identity_latex = rf"\cos(2{var}) = 2\cos^2({var}) - 1"
            expanded_expr = expr.subs(cos2_term, 2*cos(x)**2 - 1)
        else:
            identity_latex = rf"\cos(2{var}) = \cos^2({var}) - \sin^2({var})"
            expanded_expr = expr.subs(cos2_term, cos(x)**2 - sin(x)**2)

        steps.append(_limit_step(
            "Apply double-angle formula (រូបមន្តមុំទ្វេ)",
            rf"Use the double-angle identity \({identity_latex}\):"
            rf"\[ {latex(expr, ln_notation=True)} = {latex(expanded_expr, ln_notation=True)} \]",
            "trig_double_angle",
        ))
        cancelled = cancel(expanded_expr)
        if cancelled != expanded_expr:
            steps.append(_limit_step(
                "Factor and cancel common vanishing factor (សម្រួលកត្តារួម)",
                rf"Factor numerator and denominator, then cancel the common vanishing factor:"
                rf"\[ = {latex(cancelled, ln_notation=True)} \]",
                "cancel_common_factor",
            ))
            checkpoints.append({"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"})
            steps.append(_limit_step(
                "Evaluate by direct substitution (ជំនួសតម្លៃផ្ទាល់)",
                rf"Substitute \({var} = {point_latex}\): the limit evaluates to \({latex(result)}\).",
                "direct_substitution",
            ))
            checkpoints.append({"label": "final value", "value": result, "formula": "direct_substitution"})
            return steps, checkpoints

    # 4. Pythagorean identity: detect cos^2(x) with 1 - sin(x) or sin^2(x) with 1 - cos(x)
    if expr.has(cos) and expr.has(sin):
        num, den = expr.as_numer_denom()
        if den.has(cos) and not den.has(sin) and num.has(sin):
            rewritten_den = den.subs(cos(x)**2, 1 - sin(x)**2)
            num_f = factor(num)
            steps.append(_limit_step(
                "Apply Pythagorean identity (រូបមន្តគ្រឹះត្រីកោណមាត្រ)",
                rf"Use \(\cos^2({var}) = 1 - \sin^2({var}) = (1 - \sin {var})(1 + \sin {var})\):"
                rf"\[ \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{{latex(num_f)}}}{{(1 - \sin {var})(1 + \sin {var})}} \]",
                "trig_fundamental_relations",
            ))
            checkpoints.append({"label": "factored form", "value": num_f / (1 - sin(x)**2), "formula": "trig_fundamental_relations"})
            cancelled = cancel(num / rewritten_den)
            if cancelled != expr:
                steps.append(_limit_step(
                    r"Cancel common vanishing factor (សម្រួលកត្តារួម)",
                    rf"Cancel the vanishing factor \((1 - \sin {var})\):"
                    rf"\[ = {latex(cancelled, ln_notation=True)} \]",
                    "cancel_common_factor",
                ))
                checkpoints.append({"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"})
                steps.append(_limit_step(
                    "Evaluate by direct substitution (ជំនួសតម្លៃផ្ទាល់)",
                    rf"Substitute \({var} = {point_latex}\):"
                    rf"\[ \lim_{{{var} \to {point_latex}}} {latex(cancelled, ln_notation=True)} = {latex(result)} \]",
                    "direct_substitution",
                ))
                checkpoints.append({"label": "final value", "value": result, "formula": "direct_substitution"})
                return steps, checkpoints
        elif den.has(sin) and not den.has(cos) and num.has(cos):
            rewritten_den = den.subs(sin(x)**2, 1 - cos(x)**2)
            num_f = factor(num)
            steps.append(_limit_step(
                "Apply Pythagorean identity (រូបមន្តគ្រឹះត្រីកោណមាត្រ)",
                rf"Use \(\sin^2({var}) = 1 - \cos^2({var}) = (1 - \cos {var})(1 + \cos {var})\):"
                rf"\[ \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{{latex(num_f)}}}{{(1 - \cos {var})(1 + \cos {var})}} \]",
                "trig_fundamental_relations",
            ))
            checkpoints.append({"label": "factored form", "value": num_f / (1 - cos(x)**2), "formula": "trig_fundamental_relations"})
            cancelled = cancel(num / rewritten_den)
            if cancelled != expr:
                steps.append(_limit_step(
                    r"Cancel common vanishing factor (សម្រួលកត្តារួម)",
                    rf"Cancel the vanishing factor \((1 - \cos {var})\):"
                    rf"\[ = {latex(cancelled, ln_notation=True)} \]",
                    "cancel_common_factor",
                ))
                checkpoints.append({"label": "cancelled form", "value": cancelled, "formula": "cancel_common_factor"})
                steps.append(_limit_step(
                    "Evaluate by direct substitution (ជំនួសតម្លៃផ្ទាល់)",
                    rf"Substitute \({var} = {point_latex}\):"
                    rf"\[ \lim_{{{var} \to {point_latex}}} {latex(cancelled, ln_notation=True)} = {latex(result)} \]",
                    "direct_substitution",
                ))
                checkpoints.append({"label": "final value", "value": result, "formula": "direct_substitution"})
                return steps, checkpoints

    # 5. Change of variable at non-zero points (t = point - x or t = x - point)
    if point != 0 and point != S.Zero:
        steps.append(_limit_step(
            "Change of variable (ប្តូរអថេរ)",
            rf"Let \(t = {point_latex} - {var}\) (or \(t = {var} - {point_latex}\)). As \({var} \to {point_latex}\), \(t \to 0\).",
            "trig_associated_angles",
        ))
        steps.append(_limit_step(
            "Apply associated angle formulas and reduction (រូបមន្តមុំភ្ជាប់)",
            rf"Express trigonometric terms in terms of \(t\) and simplify around \(t = 0\):"
            rf"\[ {latex(expr, ln_notation=True)} \]",
            "trig_associated_angles",
        ))
        steps.append(_limit_step(
            "Evaluate limit (គណនាតម្លៃចុងក្រោយ)",
            rf"Evaluating the transformed expression as \(t \to 0\) yields \({latex(result)}\).",
            "limit_sin_x_over_x",
        ))
        checkpoints.append({"label": "final value", "value": result, "formula": "limit_sin_x_over_x"})
        return steps, checkpoints

    # 6. Algebraic simplification of trig expressions
    try:
        simp = simplify(expr)
        if simp != expr and not simp.has(oo, -oo) and simp.subs(x, point).is_finite:
            steps.append(_limit_step(
                "Simplify trigonometric expression",
                rf"Using trigonometric identities, simplify the expression:"
                rf"\[ {latex(expr, ln_notation=True)} = {latex(simp, ln_notation=True)} \]",
                formula,
            ))
            steps.append(_limit_step(
                "Evaluate by direct substitution (ជំនួសតម្លៃផ្ទាល់)",
                rf"Substitute \({var} = {point_latex}\): the limit evaluates to \({latex(result)}\).",
                "direct_substitution",
            ))
            checkpoints.append({"label": "simplified form", "value": simp, "formula": formula})
            checkpoints.append({"label": "final value", "value": result, "formula": "direct_substitution"})
            return steps, checkpoints
    except Exception:
        pass

    # Honest unclassified fallback
    steps.append(_limit_step(
        "Evaluate algebraic steps",
        rf"Transform the expression using Bac II trigonometric identities to evaluate as \({var} \to {point_latex}\):"
        rf"\[ {latex(expr, ln_notation=True)} = {latex(result)} \]",
        "unclassified_valid",
    ))
    checkpoints.append({"label": "final value", "value": result, "formula": "unclassified_valid"})
    return steps, checkpoints


def _euler_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula):
    steps = []
    checkpoints = []

    steps.append(_limit_step(
        "Verify indeterminate form 1^inf (ផ្ទៀងផ្ទាត់រាងមិនកំណត់ 1^អនន្ត)",
        rf"Substituting \({var} = {point_latex}\) into \({latex(expr, ln_notation=True)}\) gives the indeterminate form \(1^\infty\). "
        rf"We use the fundamental Euler limit formula \(\lim [f({var})]^{{g({var})}} = e^{{\lim g({var})(f({var}) - 1)}}\).",
        "euler_identify_form",
    ))

    base, pwr = expr.as_base_exp()
    u = simplify(base - 1)
    prod = pwr * u
    L = limit(prod, x, point)

    steps.append(_limit_step(
        "Compute base deviation f(x) - 1 (គណនាផលដកគោល f(x) - 1)",
        rf"Subtract \(1\) from the base: \(f({var}) - 1 = {latex(base, ln_notation=True)} - 1 = {latex(u, ln_notation=True)}\).",
        "euler_base_minus_one",
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
                "Transform exponent limit using half-angle identity (បំលែងលីមីតស្វ័យគុណតាមរូបមន្តកន្លះមុំ)",
                rf"Use \(\cos({latex(arg)}) - 1 = -2\sin^2\left({latex(half_arg)}\right)\):"
                rf"\[ g({var})(f({var}) - 1) = {latex(prod, ln_notation=True)} = {latex(sub_transformed, ln_notation=True)} \]",
                "trig_half_angle",
            ))
            checkpoints.append({"label": "exponent transformed form", "value": sub_transformed, "formula": "trig_half_angle"})
            steps.append(_limit_step(
                "Evaluate exponent limit using fundamental trig limit (គណនាលីមីតស្វ័យគុណ)",
                rf"Since \(\lim_{{u \to 0}} \dfrac{{\sin u}}{{u}} = 1\), evaluating the exponent limit gives:"
                rf"\[ L = \lim_{{{var} \to 0}} \left[{latex(sub_transformed, ln_notation=True)}\right] = {latex(L)} \]",
                "limit_sin_x_over_x",
            ))
    elif prod.has(sin) and (point == 0 or point == S.Zero):
        steps.append(_limit_step(
            "Evaluate exponent limit using fundamental trig limit (គណនាលីមីតស្វ័យគុណ)",
            rf"Using \(\lim_{{u \to 0}} \dfrac{{\sin u}}{{u}} = 1\):"
            rf"\[ L = \lim_{{{var} \to 0}} g({var})(f({var}) - 1) = \lim_{{{var} \to 0}} \left({latex(pwr, ln_notation=True)} \cdot {latex(u, ln_notation=True)}\right) = {latex(L)} \]",
            "limit_sin_x_over_x",
        ))
    else:
        steps.append(_limit_step(
            "Evaluate exponent product limit (គណនាលីមីតស្វ័យគុណ g(x)(f(x) - 1))",
            rf"Multiply by the exponent and evaluate the limit:"
            rf"\[ L = \lim_{{{var} \to {point_latex}}} g({var})(f({var}) - 1) = \lim_{{{var} \to {point_latex}}} \left({latex(pwr, ln_notation=True)} \cdot {latex(u, ln_notation=True)}\right) = {latex(L)} \]",
            "euler_exponent_limit",
        ))

    checkpoints.append({"label": "exponent limit", "value": L, "formula": "euler_exponent_limit"})

    exp_L_latex = f"e^{{{latex(L)}}}"
    res_latex = latex(result)
    conclusion_eq = f"{exp_L_latex} = {res_latex}" if exp_L_latex != res_latex else exp_L_latex
    steps.append(_limit_step(
        "Conclude with exponential result (សន្និដ្ឋានតម្លៃលីមីតចុងក្រោយ)",
        rf"Therefore, \(\lim_{{{var} \to {point_latex}}} {latex(expr, ln_notation=True)} = {conclusion_eq}\).",
        "euler_final_exp",
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
            "Try direct substitution",
            f"Substituting \\({var} = {point_latex}\\) gives an indeterminate form, so we rewrite using standard exponential limits.",
            "direct_substitution",
        )
    ]
    checkpoints = []
    if point == 0 or point == S.Zero:
        steps.append(_limit_step(
            "Isolate standard exponential limit (លីមីតអិចស្ប៉ូណង់ស្យែលគ្រឹះ)",
            rf"Divide numerator and denominator by \({var}\) to apply \(\lim_{{u \to 0}} \dfrac{{e^u - 1}}{{u}} = 1\):"
            rf"\[ {latex(expr, ln_notation=True)} \]",
            "exponential_standard_limit",
        ))
        cps = _exponential_standard_limit_checkpoints(x, point, expr, formula)
        checkpoints.extend(cps)
    steps.append(_limit_step(
        "Evaluate limit (គណនាតម្លៃចុងក្រោយ)",
        rf"Evaluating the exponential limits gives \({latex(result)}\).",
        formula,
    ))
    checkpoints.append({"label": "final value", "value": result, "formula": formula})
    return steps, checkpoints


def _logarithmic_limit_steps_checkpoints(params, var, x, point, point_latex, expr, result, formula):
    steps = [
        _limit_step(
            "Try direct substitution",
            f"Substituting \\({var} = {point_latex}\\) gives an indeterminate form, so we rewrite using logarithmic properties.",
            "direct_substitution",
        )
    ]
    checkpoints = []
    steps.append(_limit_step(
        "Reorganize using logarithmic properties",
        rf"Rewrite the expression into standard logarithmic limit form:"
        rf"\[ {latex(expr, ln_notation=True)} \]",
        "log_limit_infinity" if (point == oo or point == -oo) else "log_limit_zero",
    ))
    cps = _logarithmic_standard_limit_checkpoints(x, point, expr, formula)
    checkpoints.extend(cps)
    steps.append(_limit_step(
        "Evaluate limit (គណនាតម្លៃចុងក្រោយ)",
        rf"Evaluating the logarithmic limits gives \({latex(result)}\).",
        formula,
    ))
    checkpoints.append({"label": "final value", "value": result, "formula": formula})
    return steps, checkpoints


def _curated_limit_steps(params, var, x, point, point_latex, expr, result):
    """Curated real BAC II exercise: SymPy still computes `result` (the graded
    answer); the exam-authored technique text narrates the steps instead of a
    generic technique handler — the curated JSON only stores prose, not a
    reusable parameterized derivation. A handful of formula_names still get a
    generically-derived intermediate checkpoint (either by reusing the
    parameter-free handler for the same technique, or a bespoke generic
    deriver for `rationalization_conjugate_finite`) so correct intermediate
    work verifies instead of only the final answer."""
    formula = params["formula_name"]
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

    technique = (
        (params.get("curated_technique") or "").strip()
        or params.get("title_km")
        or _derived_technique_text(formula, var, x, point_latex, expr)
    )
    steps = [_limit_step("Apply the technique", technique, formula)]
    if params.get("curated_formula_latex"):
        steps.append(_limit_step(
            "Key identity used", f"\\({params['curated_formula_latex']}\\)", formula,
        ))
    steps.append(_limit_step(
        "Result",
        f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr, ln_notation=True)}\\) = {inline_latex(result)}.",
        formula,
    ))
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
        "Evaluate by direct substitution",
        f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr)}\\) = {inline_latex(direct)}.",
        "direct_substitution",
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
            "Try direct substitution",
            f"Substituting \\({var} = {point_latex}\\) into {inline_latex(expr)} gives \\(0/0\\), an indeterminate form, so we factor.",
            "setup_limit",
        ),
        _limit_step(
            "Factor the expression",
            f"{inline_latex(expr)} = \\(\\dfrac{{{latex(num_f)}}}{{{latex(den_f)}}}\\).",
            "factor_difference_of_squares",
        ),
        _limit_step(
            "Cancel the common factor",
            f"\\(\\dfrac{{{latex(num_f)}}}{{{latex(den_f)}}}\\) = {inline_latex(cancelled)}.",
            "cancel_common_factor",
        ),
        _limit_step(
            "Evaluate by direct substitution",
            f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(cancelled)}\\) = {inline_latex(sub_val)}.",
            "direct_substitution",
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
            "Divide numerator and denominator by the highest power",
            f"{inline_latex(expr)} = {inline_latex(divided)}.",
            "divide_highest_power",
        ),
        _limit_step(
            "Take the limit of the resulting ratio",
            f"\\(\\lim_{{{var} \\to \\infty}} {latex(divided)}\\) = {inline_latex(ratio)}.",
            "leading_coefficient_ratio",
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
            "Rewrite so the sine's argument matches the denominator",
            f"{inline_latex(expr)} = \\({coeff_prefix}{k} \\cdot \\dfrac{{\\sin({kx})}}{{{kx}}}\\).",
            "sinc_standard_limit",
        ),
        _limit_step(
            "Apply the standard sinc limit",
            f"As \\({var} \\to 0\\), \\(\\dfrac{{\\sin({kx})}}{{{kx}}} \\to 1\\), so the limit is {inline_latex(result)}.",
            "sinc_standard_limit",
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
            "Divide numerator and denominator by the variable",
            f"{inline_latex(expr)} = \\(\\dfrac{{(e^{{{a}{var}}}-1)/{var}}}{{(e^{{{b}{var}}}-1)/{var}}}\\).",
            "exponential_standard_limit",
        ),
        _limit_step(
            "Apply the standard exponential limit",
            f"As \\({var} \\to 0\\), \\(\\dfrac{{e^{{k{var}}}-1}}{{{var}}} \\to k\\) for any constant \\(k\\), so this ratio \\(\\to \\dfrac{{{a}}}{{{b}}}\\) = {inline_latex(result)}.",
            "exponential_standard_limit",
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
            "Multiply and divide by the conjugate",
            f"Multiply and divide by \\({latex(conjugate)}\\): {inline_latex(expr)} = \\(\\dfrac{{{latex(numerator)}}}{{{latex(conjugate)}}}\\).",
            "conjugate_infinity",
        ),
        _limit_step(
            "Divide numerator and denominator by the dominant power",
            f"\\(\\dfrac{{{latex(numerator)}}}{{{latex(conjugate)}}}\\) = {inline_latex(divided)}.",
            "divide_highest_power",
        ),
        _limit_step(
            "Take the limit of the resulting ratio",
            f"\\(\\lim_{{{var} \\to \\infty}} {latex(divided)}\\) = {inline_latex(result)}.",
            "leading_coefficient_ratio",
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
            "Multiply and divide by the conjugate",
            f"Since \\(\\sqrt{{{point_latex}+{c}}} = {d}\\), this is \\(0/0\\). Multiply and divide by \\({latex(conjugate)}\\): "
            f"{inline_latex(expr)} = \\(\\dfrac{{{latex(numerator_poly)} \\cdot ({latex(conjugate)})}}{{{var}-{p}}}\\).",
            "rationalization_conjugate_finite",
        ),
        _limit_step(
            "Cancel the common factor",
            f"\\(\\dfrac{{{latex(numerator_poly)}}}{{{var}-{p}}} = {latex(poly_ratio)}\\), so the expression simplifies to {inline_latex(cancelled)}.",
            "cancel_common_factor",
        ),
        _limit_step(
            "Evaluate by direct substitution",
            f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(cancelled)}\\) = {inline_latex(result)}.",
            "direct_substitution",
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
            "Multiply and divide by the conjugate",
            f"Multiply and divide by \\({latex(conjugate)}\\): {inline_latex(expr)} = "
            f"\\(\\dfrac{{2{var}}}{{\\sin({k}{var}) \\cdot ({latex(conjugate)})}}\\).",
            "rationalization_sinc_combo",
        ),
        _limit_step(
            "Split into a sinc limit and a continuous factor",
            f"\\(\\dfrac{{2{var}}}{{\\sin({k}{var})}} \\to {latex(part1)}\\) and "
            f"\\(\\dfrac{{1}}{{{latex(conjugate)}}} \\to {latex(part2)}\\) as \\({var} \\to 0\\).",
            "rationalization_sinc_combo",
        ),
        _limit_step(
            "Multiply the two limits",
            f"{inline_latex(part1)} \\(\\cdot\\) {inline_latex(part2)} = {inline_latex(result)}.",
            "rationalization_sinc_combo",
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
            "Split into a continuous factor and a sinc-squared limit",
            f"{inline_latex(expr)} = \\(\\dfrac{{(e^{{{a}{var}}}+e^{{-{a}{var}}})}}{{2}} \\cdot \\dfrac{{\\sin^2({k}{var})}}{{{var}^2}}\\).",
            "exponential_sinc_combo",
        ),
        _limit_step(
            "Evaluate each factor",
            f"As \\({var} \\to 0\\): the continuous factor \\(\\to {latex(continuous_val)}/2\\), and "
            f"\\(\\dfrac{{\\sin^2({k}{var})}}{{{var}^2}} \\to {latex(sinc_sq)}\\).",
            "exponential_sinc_combo",
        ),
        _limit_step(
            "Multiply the two limits",
            f"\\(\\dfrac{{{latex(continuous_val)}}}{{2}} \\cdot {latex(sinc_sq)}\\) = {inline_latex(result)}.",
            "exponential_sinc_combo",
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
    part1 = limit(sin(k * x) / x, x, 0)
    part2 = limit((1 - cos(m * x)) / x**2, x, 0)
    steps = [
        _limit_step(
            "Split into a sinc limit and a half-angle limit",
            f"{inline_latex(expr)} = \\(\\dfrac{{\\sin({k}{var})}}{{{var}}} \\cdot \\dfrac{{1-\\cos({m}{var})}}{{{var}^2}}\\).",
            "half_angle_sinc_combo",
        ),
        _limit_step(
            "Evaluate each factor",
            f"As \\({var} \\to 0\\): \\(\\dfrac{{\\sin({k}{var})}}{{{var}}} \\to {latex(part1)}\\), and "
            f"\\(\\dfrac{{1-\\cos({m}{var})}}{{{var}^2}} \\to {latex(part2)}\\).",
            "half_angle_sinc_combo",
        ),
        _limit_step(
            "Multiply the two limits",
            f"{inline_latex(part1)} \\(\\cdot\\) {inline_latex(part2)} = {inline_latex(result)}.",
            "half_angle_sinc_combo",
        ),
    ]
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
            "Rewrite the log difference as a single logarithm",
            f"{inline_latex(expr)} = \\({coeff_prefix}{var} \\ln\\!\\left(1+\\dfrac{{{k}}}{{{var}}}\\right)\\).",
            "log_limit_infinity",
        ),
        _limit_step(
            "Reduce to the standard log limit",
            f"With \\(u = {k}/{var} \\to 0\\), \\({var}\\ln(1+{k}/{var}) = {k} \\cdot \\dfrac{{\\ln(1+u)}}{{u}} \\to {k}\\) "
            f"since \\(\\dfrac{{\\ln(1+u)}}{{u}} \\to 1\\).",
            "log_limit_infinity",
        ),
        _limit_step(
            "Multiply by the remaining coefficient",
            f"The limit is {inline_latex(result)}.",
            "log_limit_infinity",
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
                _limit_step("Evaluate the limit at infinity", f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr)} = {latex(result)}\\).", "direct_substitution")
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

    steps = [
        _limit_step(
            "Set up the limit",
            f"\\(\\lim_{{{var} \\to {point_latex}}} {latex(expr, ln_notation=True)}\\).",
            "setup_limit",
        ),
    ]

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
    steps.extend(more_steps)

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