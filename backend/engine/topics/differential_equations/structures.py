"""Differential-equation structure registry — one entry per parameterized
exercise shape.

Mirrors ``engine/topics/derivatives/structures.py``: every equation the topic
can produce is a named structure, and a generated question records which one
it came from (``params["template_id"]``) and its slot values
(``params["template_params"]``), so the structure's blueprint (the marking
scheme, ``engine/core/blueprints.py``) can be looked up and instantiated for
it.

This registry is the topic's only question source. Two origins:

  * ``origin="sampler"`` — the shapes the old ``_sample_ode_item`` produced at
    random (one structure per root form x right-hand-side form), now named.
  * ``origin="curated"`` — shapes lifted from the textbook BAC II exercises
    that used to be replayed verbatim (a harmonic equation with its initial
    conditions at a multiple of pi, ``y'' - k^2 y = 0`` with ``x0 = ln m``,
    resonance, ``y'' + by' = k``). Every one of those 30 exercises is an
    instance of some structure here: ``CURATED_INSTANCES`` gives the slot
    values that rebuild it (``scripts/audit_ode_structures.py`` checks that
    they do).

A structure is defined the way the equations are built — from the answer
backwards, so every solution is clean:

  * the slots are the *generating* parameters: the characteristic roots
    (``r1``/``r2``, ``r``, or ``al`` +/- i ``be``) and the particular
    solution's coefficients, plus the initial conditions;
  * ``coeffs`` gives the equation's coefficients in those slots
    (``b = -(r1 + r2)``, ``c = r1*r2``);
  * ``yp`` is the particular solution, and the right-hand side is computed
    from it (``rhs = L[yp]``), never typed by hand.

``category`` is the ODE ``kind`` (the solver branch, the skill and lesson key).
Slot names avoid ``e`` (Euler's number), ``i`` (the imaginary unit), ``x``,
``y`` and ``C1``/``C2`` (the arbitrary constants).
"""
import re

from sympy import Symbol, cos, diff, expand, exp, log, pi, simplify, sin, sqrt, sympify

_X = Symbol("x")
_SLOT_RE = re.compile(r"\{(\w+)\}")

ODE_KINDS = (
    "first_order_linear_homogeneous",
    "first_order_linear_nonhomogeneous",
    "second_order_homogeneous_constant_coeff",
    "second_order_nonhomogeneous",
)

_KIND_SHORT = {
    "first_order_linear_homogeneous": "first_hom",
    "first_order_linear_nonhomogeneous": "first_nonhom",
    "second_order_homogeneous_constant_coeff": "second_hom",
    "second_order_nonhomogeneous": "second_nonhom",
}

_LOCALS = {"x": _X, "pi": pi, "exp": exp, "log": log, "sqrt": sqrt, "sin": sin, "cos": cos}


def _nz(rng, lo, hi):
    return rng.choice([v for v in range(lo, hi + 1) if v != 0])


def _sub(text, slot_values):
    """`text` with `{slot}`s replaced by `slot_values` — symbolically, so a
    negative or fractional value can't corrupt the expression."""
    names = list(dict.fromkeys(_SLOT_RE.findall(text)))
    symbols = {n: Symbol(f"_slot_{n}") for n in names}
    expr = sympify(_SLOT_RE.sub(lambda m: f"_slot_{m.group(1)}", text),
                   locals={**_LOCALS, **{f"_slot_{n}": s for n, s in symbols.items()}})
    return expr.subs({symbols[n]: sympify(slot_values[n]) for n in names})


def _second_order(struct):
    return struct["category"].startswith("second")


def _lhs(struct, y_expr, slot_values):
    """L[y] for this structure's coefficients."""
    if _second_order(struct):
        b, c = (_sub(struct["coeffs"][k], slot_values) for k in ("b", "c"))
        return diff(y_expr, _X, 2) + b * diff(y_expr, _X) + c * y_expr
    return diff(y_expr, _X) + _sub(struct["coeffs"]["a"], slot_values) * y_expr


def particular(struct, slot_values):
    """The structure's particular solution on these slot values (0 for a
    homogeneous equation)."""
    return _sub(struct["yp"], slot_values)


def _clean(expr):
    return str(simplify(expr)).replace(" ", "")


def instantiate(struct, slot_values):
    """The solver params for one instance: {"kind", "a" | "b","c", ["rhs"],
    "ics"} — the same shape the curated exercises used, so the solver and
    the prompt builder are unchanged."""
    missing = [n for n in slot_names(struct) if n not in slot_values]
    if missing:
        raise KeyError(f"{struct['id']}: missing slot values {missing}")
    params = {"kind": struct["category"]}
    for k, text in struct["coeffs"].items():
        params[k] = _clean(_sub(text, slot_values))
    if "nonhomogeneous" in struct["category"]:
        params["rhs"] = str(expand(_lhs(struct, particular(struct, slot_values), slot_values))).replace(" ", "")
    ics = {"x0": _clean(_sub(struct["ics"]["x0"], slot_values)),
           "y0": _clean(_sub(struct["ics"]["y0"], slot_values))}
    if "yp0" in struct["ics"]:
        ics["yp0"] = _clean(_sub(struct["ics"]["yp0"], slot_values))
    params["ics"] = ics
    return params


def slot_names(struct):
    return list(dict.fromkeys(_SLOT_RE.findall(struct["pattern"])))


# ---------------------------------------------------------------------------
# Samplers: draw(rng) -> slot values. The wrapper below re-rolls y(x0) when
# the initial conditions would zero every constant (the answer would just be
# the particular solution, or 0).
# ---------------------------------------------------------------------------

def _ics2(rng):
    return {"y0": rng.randint(-3, 5), "yp0": rng.randint(-5, 5)}


def _distinct_roots(rng, nonzero=False):
    pool = [v for v in range(-4, 5) if v or not nonzero]
    r1, r2 = rng.sample(pool, 2)
    return {"r1": r1, "r2": r2}


def _complex_roots(rng):
    return {"al": rng.randint(-2, 2), "be": rng.randint(1, 4)}


def _d_first_hom(rng):
    return {"a": _nz(rng, -6, 6), "y0": _nz(rng, -3, 5)}


def _d_first_const(rng):
    return {"a": _nz(rng, -4, 4), "q": _nz(rng, -5, 5), "y0": rng.randint(-3, 5)}


def _d_first_linear(rng):
    return {"a": _nz(rng, -4, 4), "p": _nz(rng, -3, 3), "q": rng.randint(-4, 4), "y0": rng.randint(-3, 5)}


def _d_first_trig(rng):
    return {"a": _nz(rng, -4, 4), "m": _nz(rng, -3, 3), "n": rng.randint(-3, 3), "y0": rng.randint(-3, 5)}


def _d_hom_distinct(rng):
    return {**_distinct_roots(rng), **_ics2(rng)}


def _d_hom_double(rng):
    return {"r": _nz(rng, -5, 5), **_ics2(rng)}


def _d_hom_complex(rng):
    return {**_complex_roots(rng), **_ics2(rng)}


def _d_hom_harmonic_shifted(rng):
    return {"w": rng.randint(1, 4), "k": rng.choice((1, 2)), **_ics2(rng)}


def _d_hom_opposite_log(rng):
    return {"k": rng.randint(1, 3), "m": rng.choice((2, 3)), **_ics2(rng)}


def _yp_const(rng):
    return {"q": _nz(rng, -5, 5)}


def _yp_linear(rng):
    return {"p": _nz(rng, -3, 3), "q": rng.randint(-4, 4)}


def _yp_quadratic(rng):
    return {"s": _nz(rng, -2, 2), "p": rng.randint(-3, 3), "q": rng.randint(-3, 3)}


def _yp_trig(rng):
    return {"k": rng.choice((1, 2)), "m": _nz(rng, -3, 3), "n": rng.randint(-2, 2)}


def _d_nonhom(roots, yp, polynomial):
    """Roots x particular-solution form. A polynomial (or constant) right-hand
    side needs c != 0 (no zero root), or the particular solution is one
    degree higher than its form; a trig one must not resonate (b = 0 and
    c = k^2: cos(kx) would already solve the homogeneous equation)."""
    def draw(rng):
        while True:
            if roots == "distinct":
                values = _distinct_roots(rng, nonzero=polynomial)
            elif roots == "double":
                values = {"r": _nz(rng, -4, 4)}
            else:
                values = _complex_roots(rng)
            values.update(yp(rng))
            if roots == "complex" and not polynomial and values["al"] == 0 and values["be"] == values["k"]:
                continue
            return {**values, **_ics2(rng)}
    return draw


def _d_resonant(rng):
    return {"w": rng.randint(1, 3), "m": _nz(rng, -4, 4), **_ics2(rng)}


def _d_zero_c(rng):
    return {"b": _nz(rng, -4, 4), "q": _nz(rng, -3, 3), **_ics2(rng)}


# ---------------------------------------------------------------------------
# The registry.
# ---------------------------------------------------------------------------

_FIRST = {"a": "{a}"}
_DISTINCT = {"b": "-({r1} + {r2})", "c": "{r1}*{r2}"}
_DOUBLE = {"b": "-2*{r}", "c": "{r}**2"}
_COMPLEX = {"b": "-2*{al}", "c": "{al}**2 + {be}**2"}
_ICS1 = {"x0": "0", "y0": "{y0}"}
_ICS2 = {"x0": "0", "y0": "{y0}", "yp0": "{yp0}"}

_YP = {
    "constant": "{q}",
    "linear": "{p}*x + {q}",
    "quadratic": "{s}*x**2 + {p}*x + {q}",
    "trig": "{m}*cos({k}*x) + {n}*sin({k}*x)",
}

_ROOT_NOTES = {
    "distinct": "r1 and r2 are distinct integers: the two real roots of the characteristic equation",
    "double": "r is a nonzero integer: the double root of the characteristic equation",
    "complex": "al (any integer, possibly 0) and be > 0 are integers: the roots are al + be*i and al - be*i",
}

_FIRST_HOM_N = "y' + ay = 0 has general solution y = Ce^{-ax}; use y(0) to find C."
_FIRST_NONHOM_N = ("Solve y' + ay = 0 (y = Ce^{-ax}), add a particular solution of the same form as "
                   "the right-hand side, then use y(0) to find C.")
_SECOND_HOM_N = {
    "distinct": "Two distinct real roots r1, r2 of r^2 + br + c = 0: y = C1 e^{r1 x} + C2 e^{r2 x}; "
                "use y(0) and y'(0) to find C1 and C2.",
    "double": "A double root r of r^2 + br + c = 0: y = (C1 + C2 x)e^{rx}; use y(0) and y'(0) to find C1 and C2.",
    "complex": "Complex roots al +/- i be of r^2 + br + c = 0: y = e^{al x}(C1 cos(be x) + C2 sin(be x)); "
               "use y(0) and y'(0) to find C1 and C2.",
}
_SECOND_NONHOM_N = ("General solution = homogeneous solution (from r^2 + br + c = 0) + a particular "
                    "solution shaped like the right-hand side; then use y(0) and y'(0) to find C1 and C2.")

_ROOT_LATEX = {
    "distinct": r"\Delta > 0",
    "double": r"\Delta = 0",
    "complex": r"\Delta < 0",
}
_RHS_LATEX = {
    "constant": "d",
    "linear": "m x + n",
    "quadratic": "u x^{2} + m x + n",
    "trig": r"m\cos(kx) + n\sin(kx)",
}
_RHS_TITLE = {"constant": "constant", "linear": "linear", "quadratic": "quadratic", "trig": "trigonometric"}
_ROOT_TITLE = {"distinct": "two real roots", "double": "a double root", "complex": "complex roots"}


def _pattern(category, coeffs, yp, ics):
    """Human-readable equation with its {slots}: every slot of the structure
    appears here (``slot_names`` reads them from it)."""
    if category.startswith("second"):
        lhs = f"y'' + ({coeffs['b']})*y' + ({coeffs['c']})*y"
        cond = f"y({ics['x0']}) = {ics['y0']}, y'({ics['x0']}) = {ics['yp0']}"
    else:
        lhs = f"y' + ({coeffs['a']})*y"
        cond = f"y({ics['x0']}) = {ics['y0']}"
    rhs = "0" if yp == "0" else f"L[{yp}]"
    return f"{lhs} = {rhs}; {cond}"


def _st(name, category, difficulty, coeffs, yp, ics, pattern_latex, title_en, draw, narration,
        slot_notes, origin="sampler"):
    struct = {
        "id": f"ode:{_KIND_SHORT[category]}:{name}",
        "question_type": "solve_ode",
        "category": category,
        "difficulty": difficulty,
        "coeffs": coeffs,
        "yp": yp,
        "ics": ics,
        "pattern": _pattern(category, coeffs, yp, ics),
        "pattern_latex": pattern_latex,
        "title_en": title_en,
        "var": "x",
        "slot_notes": slot_notes,
        "narration": narration,
        "origin": origin,
    }

    def sampler(rng):
        values = draw(rng)
        # Re-roll y(x0) while the initial conditions match the particular
        # solution (every constant would be 0).
        for _ in range(50):
            yp_ = particular(struct, values)
            x0 = _sub(ics["x0"], values)
            same = sympify(values["y0"]) == yp_.subs(_X, x0)
            if "yp0" in ics:
                same = same and sympify(values["yp0"]) == diff(yp_, _X).subs(_X, x0)
            if not same:
                break
            values["y0"] = rng.randint(-3, 5)
        return instantiate(struct, values), values

    struct["sampler"] = sampler
    return struct


def _nonhom(roots, form, difficulty, origin="sampler"):
    coeffs = {"distinct": _DISTINCT, "double": _DOUBLE, "complex": _COMPLEX}[roots]
    polynomial = form != "trig"
    yp_draw = {"constant": _yp_const, "linear": _yp_linear, "quadratic": _yp_quadratic, "trig": _yp_trig}[form]
    notes = [_ROOT_NOTES[roots],
             f"the particular solution is yp = {_YP[form].replace('{', '').replace('}', '')} "
             f"(slots {', '.join(_SLOT_RE.findall(_YP[form]))}); the right-hand side is L[yp]",
             "y0 and yp0 are the initial values y(0) and y'(0)"]
    if form == "trig" and roots == "complex":
        notes.append("never resonant: not (al = 0 and be = k)")
    return _st(
        f"{roots}_roots_{form}_rhs", "second_order_nonhomogeneous", difficulty, coeffs, _YP[form], _ICS2,
        rf"y'' + b y' + c y = {_RHS_LATEX[form]},\ {_ROOT_LATEX[roots]},\quad y(0) = y_0,\ y'(0) = y_1",
        f"y'' + by' + cy = {_RHS_TITLE[form]}, {_ROOT_TITLE[roots]}",
        _d_nonhom(roots, yp_draw, polynomial), _SECOND_NONHOM_N, notes, origin,
    )


ODE_STRUCTURES = [
    # --- first order, homogeneous ---
    _st("basic", "first_order_linear_homogeneous", "easy", _FIRST, "0", _ICS1,
        r"y' + a y = 0,\quad y(0) = y_0", "y' + ay = 0 with y(0)", _d_first_hom, _FIRST_HOM_N,
        ["a is a nonzero integer", "y0 is the initial value y(0)"]),

    # --- first order, non-homogeneous ---
    _st("constant_rhs", "first_order_linear_nonhomogeneous", "medium", _FIRST, "{q}", _ICS1,
        r"y' + a y = b,\quad y(0) = y_0", "y' + ay = constant", _d_first_const, _FIRST_NONHOM_N,
        ["a is a nonzero integer", "the particular solution is the constant yp = q; the right-hand side is a*q",
         "y0 is the initial value y(0)"]),
    _st("linear_rhs", "first_order_linear_nonhomogeneous", "medium", _FIRST, "{p}*x + {q}", _ICS1,
        r"y' + a y = m x + n,\quad y(0) = y_0", "y' + ay = linear", _d_first_linear, _FIRST_NONHOM_N,
        ["a is a nonzero integer", "the particular solution is yp = p*x + q; the right-hand side is yp' + a*yp",
         "y0 is the initial value y(0)"]),
    _st("trig_rhs", "first_order_linear_nonhomogeneous", "hard", _FIRST, "{m}*cos(x) + {n}*sin(x)", _ICS1,
        r"y' + a y = u\cos x + v\sin x,\quad y(0) = y_0", "y' + ay = trigonometric", _d_first_trig,
        _FIRST_NONHOM_N,
        ["a is a nonzero integer",
         "the particular solution is yp = m*cos(x) + n*sin(x); the right-hand side is yp' + a*yp",
         "y0 is the initial value y(0)"]),

    # --- second order, homogeneous ---
    _st("distinct_roots", "second_order_homogeneous_constant_coeff", "easy", _DISTINCT, "0", _ICS2,
        r"y'' + b y' + c y = 0,\ \Delta > 0,\quad y(0) = y_0,\ y'(0) = y_1",
        "y'' + by' + cy = 0, two real roots", _d_hom_distinct, _SECOND_HOM_N["distinct"],
        [_ROOT_NOTES["distinct"], "y0 and yp0 are the initial values y(0) and y'(0)"]),
    _st("double_root", "second_order_homogeneous_constant_coeff", "medium", _DOUBLE, "0", _ICS2,
        r"y'' + b y' + c y = 0,\ \Delta = 0,\quad y(0) = y_0,\ y'(0) = y_1",
        "y'' + by' + cy = 0, a double root", _d_hom_double, _SECOND_HOM_N["double"],
        [_ROOT_NOTES["double"], "y0 and yp0 are the initial values y(0) and y'(0)"]),
    _st("complex_roots", "second_order_homogeneous_constant_coeff", "hard", _COMPLEX, "0", _ICS2,
        r"y'' + b y' + c y = 0,\ \Delta < 0,\quad y(0) = y_0,\ y'(0) = y_1",
        "y'' + by' + cy = 0, complex roots", _d_hom_complex, _SECOND_HOM_N["complex"],
        [_ROOT_NOTES["complex"], "y0 and yp0 are the initial values y(0) and y'(0)"]),
    _st("harmonic_shifted_ic", "second_order_homogeneous_constant_coeff", "hard",
        {"b": "0", "c": "{w}**2"}, "0", {"x0": "{k}*pi/(2*{w})", "y0": "{y0}", "yp0": "{yp0}"},
        r"y'' + \omega^{2} y = 0,\quad y\!\left(\tfrac{k\pi}{2\omega}\right) = y_0,\ "
        r"y'\!\left(\tfrac{k\pi}{2\omega}\right) = y_1",
        "y'' + w^2 y = 0 with conditions at a multiple of pi", _d_hom_harmonic_shifted,
        "Roots +/- i w: y = C1 cos(wx) + C2 sin(wx); substitute x0 = k pi/(2w) into y and y' to find C1 and C2.",
        ["w is a positive integer: the roots are w*i and -w*i",
         "k is 1 or 2; the conditions are given at x0 = k*pi/(2*w)",
         "y0 and yp0 are the values y(x0) and y'(x0)"], origin="curated"),
    _st("opposite_roots_log_ic", "second_order_homogeneous_constant_coeff", "hard",
        {"b": "0", "c": "-{k}**2"}, "0", {"x0": "log({m})", "y0": "{y0}", "yp0": "{yp0}"},
        r"y'' - k^{2} y = 0,\quad y(\ln m) = y_0,\ y'(\ln m) = y_1",
        "y'' - k^2 y = 0 with conditions at ln m", _d_hom_opposite_log,
        "Roots +/- k: y = C1 e^{kx} + C2 e^{-kx}; at x0 = ln m, e^{k ln m} = m^k.",
        ["k is a positive integer: the roots are k and -k", "m is 2 or 3; the conditions are given at x0 = log(m)",
         "y0 and yp0 are the values y(x0) and y'(x0)"], origin="curated"),

    # --- second order, non-homogeneous: roots x right-hand side ---
    _nonhom("distinct", "constant", "medium"),
    _nonhom("distinct", "linear", "medium"),
    _nonhom("distinct", "quadratic", "hard"),
    _nonhom("distinct", "trig", "hard"),
    _nonhom("double", "constant", "hard"),
    _nonhom("double", "linear", "hard"),
    _nonhom("double", "quadratic", "hard"),
    _nonhom("double", "trig", "hard"),
    _nonhom("complex", "constant", "hard"),
    _nonhom("complex", "linear", "hard"),
    _nonhom("complex", "quadratic", "hard"),
    _nonhom("complex", "trig", "hard"),
    _st("resonant_sin_rhs", "second_order_nonhomogeneous", "hard", {"b": "0", "c": "{w}**2"},
        "-{m}*x*cos({w}*x)/(2*{w})", _ICS2,
        r"y'' + \omega^{2} y = m\sin(\omega x),\quad y(0) = y_0,\ y'(0) = y_1",
        "Resonance: y'' + w^2 y = m sin(wx)", _d_resonant,
        "sin(wx) already solves the homogeneous equation, so try yp = x(A cos(wx) + B sin(wx)); "
        "then use y(0) and y'(0) to find C1 and C2.",
        ["w is a positive integer: the roots are w*i and -w*i (resonance: the right-hand side solves the "
         "homogeneous equation)",
         "the particular solution is yp = -m*x*cos(w*x)/(2*w); the right-hand side is m*sin(w*x)",
         "y0 and yp0 are the initial values y(0) and y'(0)"], origin="curated"),
    _st("zero_c_constant_rhs", "second_order_nonhomogeneous", "hard", {"b": "{b}", "c": "0"}, "{q}*x", _ICS2,
        r"y'' + b y' = d,\quad y(0) = y_0,\ y'(0) = y_1",
        "y'' + by' = constant (a zero root)", _d_zero_c,
        "The roots are 0 and -b, so a constant already solves the homogeneous equation: try yp = Ax; "
        "then use y(0) and y'(0) to find C1 and C2.",
        ["b is a nonzero integer: the roots are 0 and -b",
         "the particular solution is yp = q*x; the right-hand side is b*q",
         "y0 and yp0 are the initial values y(0) and y'(0)"], origin="curated"),
]

STRUCTURES_BY_ID = {s["id"]: s for s in ODE_STRUCTURES}

#: Slot values rebuilding each textbook exercise (its curated id -> slots),
#: per structure: the 30 exercises of the former data/curated/curated.json
#: (removed; it is no longer served — each one is an instance here).
CURATED_INSTANCES = {
    "ode:first_hom:basic": {
        "p77_1": {"a": 2, "y0": 1}, "p77_1b": {"a": -3, "y0": 2}, "p77_1c": {"a": 1, "y0": -1},
    },
    "ode:first_nonhom:constant_rhs": {
        "p77_2": {"a": 3, "q": 3, "y0": 5}, "p77_2b": {"a": 2, "q": 2, "y0": 0},
        "p77_2c": {"a": -2, "q": 3, "y0": 1},
    },
    "ode:first_nonhom:linear_rhs": {
        "p77_3": {"a": -2, "p": -2, "q": -1, "y0": 1}, "p77_3b": {"a": 1, "p": 2, "q": 1, "y0": 2},
    },
    "ode:first_nonhom:trig_rhs": {"p77_4": {"a": -1, "m": -1, "n": 0, "y0": 0}},
    "ode:second_hom:distinct_roots": {
        "p78_4": {"r1": 2, "r2": 3, "y0": 2, "yp0": 5}, "p78_4b": {"r1": 3, "r2": -2, "y0": 1, "yp0": -8},
        "p78_4c": {"r1": 1, "r2": -2, "y0": 1, "yp0": -8}, "p78_4d": {"r1": 4, "r2": -1, "y0": 3, "yp0": -8},
        "p79_7": {"r1": 1, "r2": 3, "y0": 3, "yp0": 5},
    },
    "ode:second_hom:double_root": {
        "p78_5": {"r": 2, "y0": 1, "yp0": 0}, "p78_5b": {"r": -1, "y0": -3, "yp0": 2},
        "p78_5c": {"r": 3, "y0": 1, "yp0": 4}, "p79_8b": {"r": 5, "y0": 1, "yp0": 0},
    },
    "ode:second_hom:complex_roots": {
        "p78_6": {"al": 1, "be": 1, "y0": 1, "yp0": 1}, "p78_6b": {"al": -1, "be": 2, "y0": 0, "yp0": 1},
        "p79_8": {"al": 0, "be": 4, "y0": 2, "yp0": -2},
    },
    "ode:second_hom:harmonic_shifted_ic": {
        "p78_6c": {"w": 1, "k": 1, "y0": 3, "yp0": 2}, "p78_6d": {"w": 4, "k": 2, "y0": "sqrt(3)", "yp0": 4},
    },
    "ode:second_hom:opposite_roots_log_ic": {"p79_8c": {"k": 3, "m": 2, "y0": 1, "yp0": -3}},
    "ode:second_nonhom:distinct_roots_linear_rhs": {
        "p79_9b": {"r1": 1, "r2": 2, "p": 1, "q": 2, "y0": 3, "yp0": 4},
    },
    "ode:second_nonhom:complex_roots_linear_rhs": {
        "p79_9": {"al": 0, "be": 2, "p": "3/2", "q": 0, "y0": 1, "yp0": 0},
    },
    "ode:second_nonhom:complex_roots_quadratic_rhs": {
        "p83_11": {"al": 0, "be": 2, "s": "1/4", "p": "1/2", "q": "-3/8", "y0": 0, "yp0": 0},
    },
    "ode:second_nonhom:complex_roots_trig_rhs": {
        "p84_10": {"al": 0, "be": 3, "k": 1, "m": "1/4", "n": 0, "y0": 0, "yp0": 0},
    },
    "ode:second_nonhom:resonant_sin_rhs": {"p84_12": {"w": 1, "m": 1, "y0": 0, "yp0": 1}},
    "ode:second_nonhom:zero_c_constant_rhs": {"p83_10": {"b": 3, "q": "5/3", "y0": "exp(3)", "yp0": "2/3"}},
}

for _s in ODE_STRUCTURES:
    _s["source_labels"] = list(CURATED_INSTANCES.get(_s["id"], {}))


def all_ode_structures():
    return list(ODE_STRUCTURES)
