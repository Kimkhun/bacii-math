"""Differential-equation solver (curated BAC II exercises): SymPy's ``dsolve``
computes the real general or particular solution; the curated JSON only
supplies the equation's shape (kind + coefficients + optional initial
conditions) and the exam-authored technique narration."""
from sympy import Derivative, Eq, Function, Symbol, latex, sympify

from .shared import _calc_locals, _formula_tags

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

    result = dsolve(equation, y(x), ics=ics) if ics else dsolve(equation, y(x))
    answer = result.rhs

    steps.append(_step("Result", f"\\({latex(result)}\\)."))

    checkpoints = [{"label": "y(x)", "value": answer, "formula": "solve_ode"}]
    return {
        "answer_exact": answer,
        "answer_decimal": None,
        "answer_latex": latex(answer),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
    }
