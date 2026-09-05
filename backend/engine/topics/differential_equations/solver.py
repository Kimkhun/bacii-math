"""Differential-equation solver (curated BAC II exercises): SymPy's ``dsolve``
computes the real general or particular solution; the curated JSON only
supplies the equation's shape (kind + coefficients + optional initial
conditions) and the exam-authored technique narration."""
from sympy import (
    Derivative, Eq, Function, Symbol, cos, exp, im, latex, re, simplify, sin,
    solve as sym_solve, sympify,
)

from ...core.shared import _calc_locals, _formula_tags

try:
    from sympy import dsolve
except ImportError:  # pragma: no cover
    dsolve = None


def _step(title, detail, formula="solve_ode"):
    return {"title": title, "detail": detail, "formula": formula}


def _build_equation(kind, params, x, y):
    locals_ = _calc_locals("x")
    y_expr = y(x)
    if kind == "first_order_linear_homogeneous":
        a = sympify(params["a"], locals=locals_)
        lhs = Derivative(y_expr, x) + a * y_expr
        return Eq(lhs, 0)
    if kind == "first_order_linear_nonhomogeneous":
        a = sympify(params["a"], locals=locals_)
        rhs = sympify(params["rhs"], locals=locals_)
        lhs = Derivative(y_expr, x) + a * y_expr
        return Eq(lhs, rhs)
    if kind == "second_order_homogeneous_constant_coeff":
        b = sympify(params["b"], locals=locals_)
        c = sympify(params["c"], locals=locals_)
        lhs = Derivative(y_expr, x, 2) + b * Derivative(y_expr, x) + c * y_expr
        return Eq(lhs, 0)
    if kind == "second_order_nonhomogeneous":
        b = sympify(params["b"], locals=locals_)
        c = sympify(params["c"], locals=locals_)
        rhs = sympify(params["rhs"], locals=locals_)
        lhs = Derivative(y_expr, x, 2) + b * Derivative(y_expr, x) + c * y_expr
        return Eq(lhs, rhs)
    raise ValueError(f"unknown differential-equation kind: {kind}")


def _build_ics(ics, x, y):
    if not ics:
        return None
    locals_ = _calc_locals("x")
    x0 = sympify(ics["x0"], locals=locals_)
    out = {y(x0): sympify(ics["y0"], locals=locals_)}
    if ics.get("yp0") is not None:
        out[Derivative(y(x), x).subs(x, x0)] = sympify(ics["yp0"], locals=locals_)
    return out


def _constant_checkpoints(general_rhs, ics_raw, x):
    """Solve for the arbitrary constants (C1, C2, ...) in the general solution
    directly from the initial conditions, so each one can be checked as its
    own line ("C1 = -3") rather than only the fully-substituted y(x)."""
    const_syms = sorted(general_rhs.free_symbols - {x}, key=str)
    if not const_syms:
        return []
    locals_ = _calc_locals("x")
    x0 = sympify(ics_raw["x0"], locals=locals_)
    y0 = sympify(ics_raw["y0"], locals=locals_)
    eqs = [Eq(general_rhs.subs(x, x0), y0)]
    if ics_raw.get("yp0") is not None:
        yp0 = sympify(ics_raw["yp0"], locals=locals_)
        eqs.append(Eq(general_rhs.diff(x).subs(x, x0), yp0))
    try:
        solved = sym_solve(eqs, const_syms, dict=True)
    except Exception:
        return []
    if not solved:
        return []
    values = solved[0]
    return [
        {"label": str(sym), "value": values[sym], "formula": "solve_ode"}
        for sym in const_syms if sym in values
    ]


def _relabeled_homogeneous_solution(roots, x):
    """Build the homogeneous part of the general solution with C1/C2 assigned
    to match the curated narration's convention (C1 paired with the first
    root / constant term / cos coefficient, C2 with the second root / x
    coefficient / sin coefficient) rather than whichever internal symbols
    SymPy's ``dsolve`` happens to pick — dsolve is free to name the sin
    coefficient "C1" and the cos coefficient "C2", which then disagrees with
    the curated step text ("y=e^{x}(C_1\\cos x+C_2\\sin x)") and marks a
    student's correctly-labeled C1/C2 values wrong."""
    C1, C2 = Symbol("C1"), Symbol("C2")
    r1 = roots[0]
    r2 = roots[1] if len(roots) > 1 else roots[0]
    if r1 == r2:
        return (C1 + C2 * x) * exp(r1 * x)
    if r1.is_real and r2.is_real:
        return C1 * exp(r1 * x) + C2 * exp(r2 * x)
    alpha = re(r1)
    beta = abs(im(r1))
    return exp(alpha * x) * (C1 * cos(beta * x) + C2 * sin(beta * x))


def _solve_differential_equation(params):
    x = Symbol("x")
    y = Function("y")
    kind = params["kind"]
    equation = _build_equation(kind, params, x, y)
    ics = _build_ics(params.get("ics"), x, y)

    steps = [_step(
        "Set up the differential equation",
        f"Solve \\({latex(equation)}\\)" + (" with the given initial conditions." if ics else " (general solution)."),
    )]
    steps.append(_step("Apply the technique", params.get("curated_technique", "")))

    general = dsolve(equation, y(x))
    result = dsolve(equation, y(x), ics=ics) if ics else general
    answer = result.rhs

    steps.append(_step("Result", f"\\({latex(result)}\\)."))

    checkpoints = []
    given_equations = []

    general_rhs = general.rhs
    # Characteristic-equation roots are a distinct, checkable intermediate
    # value for the constant-coefficient kinds (the homogeneous part of a
    # non-homogeneous equation too) — without these, a student's correct
    # "r = -1" line has nothing to match but the final y(x). The equation
    # itself ("r^2 + 2r + 1 = 0") is exposed as a given_equation so a
    # restatement of it is skipped rather than flagged as a wrong value.
    if kind in ("second_order_homogeneous_constant_coeff", "second_order_nonhomogeneous"):
        r = Symbol("r")
        b = sympify(params["b"], locals=_calc_locals("x"))
        c = sympify(params["c"], locals=_calc_locals("x"))
        char_eq = Eq(r**2 + b * r + c, 0)
        given_equations.append(char_eq)
        roots = sym_solve(char_eq, r)
        for root in roots:
            checkpoints.append({"label": "characteristic root", "value": root, "formula": "solve_ode"})

        # dsolve's own C1/C2 assignment for the homogeneous part is
        # arbitrary and can disagree with the curated narration's
        # convention (e.g. naming the sin coefficient "C1"). Rebuild the
        # general solution with C1/C2 relabeled to match that convention —
        # the non-homogeneous particular part (unique, no naming ambiguity)
        # is recovered by zeroing dsolve's constants, which vanishes exactly
        # the homogeneous combination since it's linear in them.
        dsolve_consts = sorted(general.rhs.free_symbols - {x}, key=str)
        particular = general.rhs.subs({c_: 0 for c_ in dsolve_consts}) if kind == "second_order_nonhomogeneous" else 0
        general_rhs = simplify(particular + _relabeled_homogeneous_solution(roots, x))

    # The general solution (and its derivative), still symbolic in the
    # arbitrary constants, is written out verbatim on the way to the
    # particular solution — a restatement of setup, not a new computed
    # value, so it's skipped rather than checked like a piecewise branch
    # formula is for continuity.
    given_expressions = [general_rhs, general_rhs.diff(x)]

    # When initial conditions pin down the arbitrary constants, expose each
    # solved constant (C1, C2, ...) as its own checkpoint so a student's
    # "C1 = -3" / "C2 = -1" lines are checked against the right target
    # instead of only the fully-substituted final y(x).
    ics_raw = params.get("ics")
    if ics_raw:
        checkpoints.extend(_constant_checkpoints(general_rhs, ics_raw, x))
        # The IC equations after substituting x0 into the general solution
        # (e.g. "y'(0) = C2 - C1 = 2") are themselves restated verbatim on
        # the way to solving for the constants — expose them so that
        # restatement is skipped rather than checked against a checkpoint
        # value it was never meant to match.
        locals_ = _calc_locals("x")
        x0 = sympify(ics_raw["x0"], locals=locals_)
        y0 = sympify(ics_raw["y0"], locals=locals_)
        given_equations.append(Eq(general_rhs.subs(x, x0), y0))
        if ics_raw.get("yp0") is not None:
            yp0 = sympify(ics_raw["yp0"], locals=locals_)
            given_equations.append(Eq(general_rhs.diff(x).subs(x, x0), yp0))

    checkpoints.append({"label": "y(x)", "value": answer, "formula": "solve_ode"})
    return {
        "answer_exact": answer,
        "answer_decimal": None,
        "answer_latex": latex(answer),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
        "given_expressions": given_expressions,
        "given_equations": given_equations,
    }
