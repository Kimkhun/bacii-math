"""Conics solver (curated BAC II exercises): SymPy completes the square on the
general-form equation to derive the real vertex/center/focus/asymptote data
(parabola / ellipse / hyperbola, either axis orientation); the curated JSON
only supplies the general-form equation, which single derived quantity to
grade (``ask``), and the exam-authored technique narration."""
from sympy import Symbol, expand, latex, simplify, sqrt, sympify

from ...core.shared import _formula_tags

_X, _Y = Symbol("x"), Symbol("y")


def _step(title, detail, formula="conic_classification"):
    return {"title": title, "detail": detail, "formula": formula}


def _classify(expr):
    Ax, Ay = expr.coeff(_X, 2), expr.coeff(_Y, 2)
    Bx, By = expr.coeff(_X, 1), expr.coeff(_Y, 1)
    const = simplify(expr - Ax * _X**2 - Bx * _X - Ay * _Y**2 - By * _Y)

    if Ax == 0 and Ay != 0:
        k = -By / (2 * Ay)
        remainder = const - By**2 / (4 * Ay)
        h = -remainder / Bx
        p = 1 / (4 * (-Ay / Bx))
        return {"type": "parabola", "axis": "x", "vertex": (h, k), "p": p,
                "focus": (h + p, k), "directrix": h - p}
    if Ay == 0 and Ax != 0:
        h = -Bx / (2 * Ax)
        remainder = const - Bx**2 / (4 * Ax)
        k = -remainder / By
        p = 1 / (4 * (-Ax / By))
        return {"type": "parabola", "axis": "y", "vertex": (h, k), "p": p,
                "focus": (h, k + p), "directrix": k - p}

    h, k = -Bx / (2 * Ax), -By / (2 * Ay)
    rhs = -(const - Bx**2 / (4 * Ax) - By**2 / (4 * Ay))
    a2_x, a2_y = rhs / Ax, rhs / Ay
    if Ax * Ay > 0:
        major = "x" if a2_x > a2_y else "y"
        a2, b2 = max(a2_x, a2_y), min(a2_x, a2_y)
        c = sqrt(a2 - b2)
        return {"type": "ellipse", "center": (h, k), "a2": a2, "b2": b2, "c": c, "major_axis": major}

    if a2_x > 0:
        a2, b2, axis = a2_x, -a2_y, "x"
    else:
        a2, b2, axis = a2_y, -a2_x, "y"
    c = sqrt(a2 + b2)
    return {"type": "hyperbola", "center": (h, k), "a2": a2, "b2": b2, "c": c, "transverse_axis": axis}


_ASK_LABELS = {
    "vertex_x": "vertex x-coordinate", "vertex_y": "vertex y-coordinate", "p": "focal parameter p",
    "focus_x": "focus x-coordinate", "focus_y": "focus y-coordinate", "directrix": "directrix constant",
    "center_x": "center x-coordinate", "center_y": "center y-coordinate",
    "a": "semi-major/transverse axis length a", "b": "semi-minor/conjugate axis length b", "c": "focal distance c",
}


def _extract_ask(info, ask):
    if info["type"] == "parabola":
        if ask == "vertex_x":
            return info["vertex"][0]
        if ask == "vertex_y":
            return info["vertex"][1]
        if ask == "p":
            return info["p"]
        if ask == "focus_x":
            return info["focus"][0]
        if ask == "focus_y":
            return info["focus"][1]
        if ask == "directrix":
            return info["directrix"]
    else:
        if ask == "center_x":
            return info["center"][0]
        if ask == "center_y":
            return info["center"][1]
        if ask == "a":
            return sqrt(info["a2"])
        if ask == "b":
            return sqrt(info["b2"])
        if ask == "c":
            return info["c"]
    raise ValueError(f"ask '{ask}' does not apply to a {info['type']}")


def _describe(info):
    if info["type"] == "parabola":
        h, k = info["vertex"]
        return (f"Parabola with vertex \\(({latex(h)}, {latex(k)})\\), "
                f"focal parameter \\(p={latex(info['p'])}\\), "
                f"focus \\(({latex(info['focus'][0])}, {latex(info['focus'][1])})\\), "
                f"directrix \\({'x' if info['axis']=='x' else 'y'} = {latex(info['directrix'])}\\).")
    h, k = info["center"]
    a, b, c = sqrt(info["a2"]), sqrt(info["b2"]), info["c"]
    kind = "Ellipse" if info["type"] == "ellipse" else "Hyperbola"
    return (f"{kind} with center \\(({latex(h)}, {latex(k)})\\), "
            f"\\(a={latex(a)}\\), \\(b={latex(b)}\\), \\(c={latex(c)}\\).")


def _solve_conic(params):
    expr = expand(sympify(params["expr"], locals={"x": _X, "y": _Y}))
    info = _classify(expr)
    ask = params["ask"]
    result = _extract_ask(info, ask)

    steps = [
        _step("Complete the square", f"Rewrite \\({latex(expr)} = 0\\) in standard conic form."),
        _step("Apply the technique", params.get("curated_technique", "")),
        _step("Classify and extract features", _describe(info)),
        _step("Result", f"The requested quantity ({_ASK_LABELS.get(ask, ask)}) is \\({latex(result)}\\)."),
    ]
    checkpoints = [{"label": ask, "value": result, "formula": "conic_classification"}]
    return {
        "answer_exact": result,
        "answer_decimal": _safe_float(result),
        "answer_latex": latex(result),
        "steps": steps,
        "formula_tags": _formula_tags(steps),
        "checkpoints": checkpoints,
    }


def _safe_float(value):
    try:
        from sympy import N
        return float(N(value, 8))
    except (TypeError, ValueError):
        return None
