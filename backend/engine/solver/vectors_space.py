"""3D vector solver (curated BAC II exercises): SymPy Matrix operations
compute the real magnitude/dot/cross/area/triple-product/orthogonality
result; the curated JSON only supplies the point or vector coordinates and
the exam-authored technique narration."""
from sympy import Eq, Matrix, Rational, Symbol, latex, solve, sqrt, sympify

from .shared import _formula_tags


def _step(title, detail, formula="vector_ops"):
    return {"title": title, "detail": detail, "formula": formula}


def _vec(coords, locals_=None):
    return Matrix([sympify(c, locals=locals_ or {}) if isinstance(c, str) else Rational(c) for c in coords])


def _sub(p, q):
    return Matrix([b - a for a, b in zip(p, q)])


def _magnitude(v):
    return sqrt(sum(c**2 for c in v))


def _solve_vector_ops(params):
    op = params["op"]
    steps = [_step("Apply the technique", params.get("curated_technique", ""))]

    if op == "magnitude":
        A, B = _vec(params["A"]), _vec(params["B"])
        ab = B - A
        result = _magnitude(ab)
        steps.append(_step("Compute the vector", f"\\(\\overrightarrow{{AB}} = {latex(ab.T)}\\)."))
        steps.append(_step("Compute the magnitude", f"\\(|\\overrightarrow{{AB}}| = {latex(result)}\\)."))

    elif op == "distance":
        A, B = _vec(params["A"]), _vec(params["B"])
        result = _magnitude(B - A)
        steps.append(_step("Compute the distance", f"\\(AB = {latex(result)}\\)."))

    elif op == "dot":
        A, B, C = _vec(params["A"]), _vec(params["B"]), _vec(params["C"])
        ab, ac = B - A, C - A
        result = (ab.T * ac)[0]
        steps.append(_step("Build the vectors", f"\\(\\overrightarrow{{AB}} = {latex(ab.T)},\\ \\overrightarrow{{AC}} = {latex(ac.T)}\\)."))
        steps.append(_step("Compute the dot product", f"\\(\\overrightarrow{{AB}}\\cdot\\overrightarrow{{AC}} = {latex(result)}\\)."))

    elif op == "cross_magnitude":
        A, B, C = _vec(params["A"]), _vec(params["B"]), _vec(params["C"])
        ab, ac = B - A, C - A
        cross = ab.cross(ac)
        result = _magnitude(cross)
        steps.append(_step("Build the vectors", f"\\(\\overrightarrow{{AB}} = {latex(ab.T)},\\ \\overrightarrow{{AC}} = {latex(ac.T)}\\)."))
        steps.append(_step("Compute the cross product", f"\\(\\overrightarrow{{AB}}\\times\\overrightarrow{{AC}} = {latex(cross.T)}\\)."))
        steps.append(_step("Compute its magnitude", f"\\(|\\overrightarrow{{AB}}\\times\\overrightarrow{{AC}}| = {latex(result)}\\)."))

    elif op == "triangle_area":
        A, B, C = _vec(params["A"]), _vec(params["B"]), _vec(params["C"])
        ab, ac = B - A, C - A
        cross = ab.cross(ac)
        result = _magnitude(cross) / 2
        steps.append(_step("Compute the cross product", f"\\(\\overrightarrow{{AB}}\\times\\overrightarrow{{AC}} = {latex(cross.T)}\\)."))
        steps.append(_step("Halve its magnitude", f"Area \\(= \\tfrac12|\\overrightarrow{{AB}}\\times\\overrightarrow{{AC}}| = {latex(result)}\\)."))

    elif op == "scalar_triple_product":
        u, v, w = _vec(params["u"]), _vec(params["v"]), _vec(params["w"])
        result = (u.T * v.cross(w))[0]
        steps.append(_step("Compute v x w", f"\\(\\vec v\\times\\vec w = {latex(v.cross(w).T)}\\)."))
        steps.append(_step("Dot with u", f"\\(\\vec u\\cdot(\\vec v\\times\\vec w) = {latex(result)}\\)."))

    elif op == "find_m_orthogonal":
        m = Symbol(params["unknown"])
        locals_ = {params["unknown"]: m}
        u, v = _vec(params["u"], locals_), _vec(params["v"], locals_)
        dot = (u.T * v)[0]
        solutions = solve(Eq(dot, 0), m)
        result = solutions[0] if solutions else None
        steps.append(_step("Set up the orthogonality condition", f"\\(\\vec u\\cdot\\vec v = {latex(dot)} = 0\\)."))
        steps.append(_step("Solve for the unknown", f"\\({params['unknown']} = {latex(result)}\\)."))

    else:
        raise ValueError(f"unknown vector op: {op}")

    checkpoints = [{"label": op, "value": result, "formula": "vector_ops"}]
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
