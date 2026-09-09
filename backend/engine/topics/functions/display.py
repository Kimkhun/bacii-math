"""Template-driven Khmer/English rendering for function-study answers.

The math is always computed by SymPy (see ``functions.py``); this module only
turns the computed values into display strings and a line-per-step narrative.
Every ``want`` type has a template that takes a small structured ``ctx`` (the
values the solver already computed) plus the variable and function name, and
returns the final-answer line in both English and Khmer. A second registry
produces the step-by-step narrative (``solution_km``/``solution_en``).

Nothing here hardcodes a computed value: only the *wording* is templated. The
JSON ``display``/``technique`` fields remain optional overrides for special
official forms (e.g. the area's three equivalent log expressions); when absent
the templates generate everything.

Khmer phrasing is derived from the verified 2025 BAC II key
(``data/curated/2025.json``).
"""
from sympy import latex

from ...core.shared import inline_latex


def _ln(s):
    """Normalise SymPy's \\log output to \\ln (the 2025 BAC II key's convention)."""
    return s.replace("\\log", "\\ln")

# --- Curated Khmer math phrase glossary (source of truth: 2025 key) ----------
KHMER = {
    "domain": "ដែនកំណត់",
    "domain_of": "ដែនកំណត់នៃ",
    "odd": "អនុគមន៍សេស",
    "even": "អនុគមន៍គូ",
    "neither": "មិនគូមិនសេស",
    "is_odd": "ជាអនុគមន៍សេស",
    "is_even": "ជាអនុគមន៍គូ",
    "is_neither": "មិនមែនគូ និងមិនមែនសេស",
    "limit": "លីមីត",
    "increasing": "កើន",
    "decreasing": "ចុះ",
    "constant": "ថេរ",
    "variation_table": "តារាងអថេរភាព",
    "tangent": "បន្ទាត់ប៉ះ",
    "tangent_eq": "សមីការបន្ទាត់ប៉ះ",
    "draw": "សង់ក្រាប",
    "sign": "សញ្ញា",
    "asymptote_vertical": "អាស៊ីមតូតឈរ",
    "asymptote_horizontal": "អាស៊ីមតូតផ្ដេក",
    "asymptote_oblique": "អាស៊ីមតូតទ្រេត",
    "square_units": "ឯកតាផ្ទៃ",
    "above": "ខាងលើ",
    "below": "ខាងក្រោម",
    "center_symmetry": "ចំណុចកណ្ដាលស៊ីមេទ្រី",
    "answer": "ចម្លើយ",
    "therefore": "ដូច្នេះ",
    "on": "លើ",
    "we_get": "គេបាន",
    "with": "ជាមួយ",
}

# --- English phrase glossary --------------------------------------------------
EN = {
    "domain": "Domain",
    "domain_of": "domain of",
    "odd": "odd function",
    "even": "even function",
    "neither": "neither even nor odd",
    "is_odd": "is odd",
    "is_even": "is even",
    "is_neither": "is neither even nor odd",
    "limit": "limit",
    "increasing": "increasing",
    "decreasing": "decreasing",
    "constant": "constant",
    "variation_table": "variation table",
    "tangent": "tangent line",
    "tangent_eq": "equation of the tangent line",
    "draw": "draw the graph",
    "sign": "sign",
    "asymptote_vertical": "vertical asymptote",
    "asymptote_horizontal": "horizontal asymptote",
    "asymptote_oblique": "oblique asymptote",
    "square_units": "square units",
    "above": "above",
    "below": "below",
    "center_symmetry": "center of symmetry",
    "answer": "Answer",
    "therefore": "therefore",
    "on": "on",
    "we_get": "we get",
    "with": "with",
}

_DIRECTION_KM = {"inc": "កើន", "dec": "ចុះ"}
_DIRECTION_EN = {"inc": "increasing", "dec": "decreasing"}


# --- small numeric/interval helpers (moved here from functions.py) -----------
def _f(v):
    from sympy import N, oo

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


def _km_infty(v):
    from sympy import oo

    if v == oo:
        return "+∞"
    if v == -oo:
        return "−∞"
    return str(v)


# --- answer template registry ------------------------------------------------
# Each entry: ctx -> (en, km). ctx carries the want-specific computed values.


def _t_domain(ctx, var, fn, G):
    return f"{G['domain']} D = {ctx['interval']}", f"{G['domain']} D = {ctx['interval']}"


def _t_parity(ctx, var, fn, G):
    key = {"odd": "is_odd", "even": "is_even", "neither": "is_neither"}.get(ctx["verdict"], "is_neither")
    return f"{fn} {G[key]}", f"{fn} {G[key]}"


def _t_limit(ctx, var, fn, G):
    side = ctx.get("side")
    sgn = "+" if side == "+" else ("-" if side == "-" else "")
    point = ctx.get("point")
    if not point:
        return None
    value = ctx.get("value_latex") if ctx.get("infinite") else str(ctx.get("value"))
    return f"lim{{x→{point}{sgn}}} {fn}(x) = {value}", (
        f"lim{{x→{point}{sgn}}} {fn}(x) = {value}"
    )


def _t_limits(ctx, var, fn, G):
    parts = [f"lim{{x→{r['point']}}} {fn}(x) = {r['value']}" for r in ctx["results"]]
    return "; ".join(parts), "; ".join(parts)


def _t_derivative(ctx, var, fn, G):
    expr = ctx.get("expr_latex") or ctx.get("expr") or ""
    return f"{fn}'({var}) = {expr}", f"{fn}'({var}) = {expr}"


def _t_monotonicity(ctx, var, fn, G):
    pieces = []
    for p in ctx["pieces"]:
        word = _DIRECTION_KM[p["direction"]] if G is KHMER else _DIRECTION_EN[p["direction"]]
        pieces.append(f"{word} {G['on']} {p['interval']}")
    return "; ".join(pieces) or G["constant"], "; ".join(pieces) or G["constant"]


def _t_sign(ctx, var, fn, G):
    neg = ctx.get("neg") or "∅"
    pos = ctx.get("pos") or "∅"
    return (f"{fn}({var}) < 0 {G['on']} {neg} ; {fn}({var}) > 0 {G['on']} {pos}",
            f"{fn}({var}) < 0 {G['on']} {neg} ; {fn}({var}) > 0 {G['on']} {pos}")


def _t_variation_table(ctx, var, fn, G):
    return G["variation_table"], G["variation_table"]


def _t_tangent(ctx, var, fn, G):
    line = ctx.get("line_latex") or ctx.get("line") or ""
    return (f"{G['tangent_eq']} T: y = {line}", f"{G['tangent_eq']} T: y = {line}")


def _t_draw(ctx, var, fn, G):
    return (f"{G['draw']} C {G['with']} {G['tangent']} T",
            f"{G['draw']} C {G['with']} {G['tangent']} T")


def _t_derivative_product(ctx, var, fn, G):
    h = ctx.get("h_fn") or "h"
    expr = ctx.get("expr_latex") or ctx.get("expr") or ""
    return f"{h}'({var}) = {expr}", f"{h}'({var}) = {expr}"


def _t_integral(ctx, var, fn, G):
    value = ctx.get("value_latex") or str(ctx.get("value") or "")
    return f"S = {value} {G['square_units']}", f"S = {value} {G['square_units']}"


def _t_asymptote(ctx, var, fn, G):
    line = ctx.get("line_latex") or ctx.get("line") or ""
    kind = ctx.get("kind", "oblique")
    key = f"asymptote_{kind}"
    label = G.get(key, G["asymptote_oblique"])
    return f"{label} y = {line}", f"{label} y = {line}"


def _t_decompose(ctx, var, fn, G):
    dec = ctx.get("dec_latex") or ctx.get("dec") or ""
    a, b, c = ctx.get("a"), ctx.get("b"), ctx.get("c")
    base = f"{fn}({var}) = {dec}"
    if None not in (a, b, c):
        base += f",  a={a}, b={b}, c={c}"
    return base, base


def _t_position(ctx, var, fn, G):
    above = ctx.get("above") or "∅"
    below = ctx.get("below") or "∅"
    return (f"C {G['above']} d {G['on']} {above} ; C {G['below']} d {G['on']} {below}",
            f"C {G['above']} d {G['on']} {above} ; C {G['below']} d {G['on']} {below}")


def _t_symmetry(ctx, var, fn, G):
    if ctx.get("center"):
        return f"I {G['center_symmetry']} of C", f"I {G['center_symmetry']} of C"
    if G is KHMER:
        return "I មិនមែនជាចំណុចកណ្ដាលស៊ីមេទ្រីរបស់ C", "I មិនមែនជាចំណុចកណ្ដាលស៊ីមេទ្រីរបស់ C"
    return "I is not the center of symmetry of C", "I is not the center of symmetry of C"


_ANSWER_TEMPLATES = {
    "domain": _t_domain,
    "parity": _t_parity,
    "limit": _t_limit,
    "limits": _t_limits,
    "derivative": _t_derivative,
    "monotonicity": _t_monotonicity,
    "sign": _t_sign,
    "variation_table": _t_variation_table,
    "tangent": _t_tangent,
    "draw": _t_draw,
    "derivative_product": _t_derivative_product,
    "integral": _t_integral,
    "asymptote": _t_asymptote,
    "decompose": _t_decompose,
    "position": _t_position,
    "symmetry": _t_symmetry,
}


def render_answer(want, ctx, var="x", fn="f", lang="km"):
    """Return the final-answer line for a want from its structured ctx."""
    G = KHMER if lang == "km" else EN
    tpl = _ANSWER_TEMPLATES.get(want)
    if tpl is None:
        return None
    try:
        en, km = tpl(ctx, var, fn, G)
        return km if lang == "km" else en
    except Exception:
        return None
# --- step-narrative registry --------------------------------------------------
# Shape-aware. Each entry: ctx, var, fn -> list of lines (one per math step).
# `question_km` is prepended and the answer line appended by the caller.
# The log-shape templates mirror the verified 2025 BAC II key line-for-line.

_D = {"inc": "កើន", "dec": "ចុះ"}
_D_EN = {"inc": "increasing", "dec": "decreasing"}


def _j(cond, a, b):
    return a if cond else b


# ---------- LOG shape (mirrors 2025 extraction exactly) ----------
def _sl_domain(ctx, var, fn, G):
    km = G is KHMER
    fn = ctx.get("fn", fn)
    num, den = ctx.get("num", "?"), ctx.get("den", "?")
    lines = [
        f"អនុគមន៍ ${fn}$ កំណត់បានលុះត្រា $\\left(\\frac{{{num}}}{{{den}}}\\right) > 0$" if km
        else f"The function ${fn}$ is defined only when $\\left(\\frac{{{num}}}{{{den}}}\\right) > 0$"
    ]
    for r in ctx.get("P_eq_zero", []):
        lines.append(f"បើ ${num} = 0$ នោះ $x = {r}$" if km else f"If ${num} = 0$, then $x = {r}$")
    for r in ctx.get("Q_eq_zero", []):
        lines.append(f"បើ ${den} = 0$ នោះ $x = {r}$" if km else f"If ${den} = 0$, then $x = {r}$")
    lines.append(_sign_table_text(ctx.get("sign_rows"), km))
    lines.append(f"ដូច្នេះ $D = {ctx['interval']}$ ។" if km else f"Therefore $D = {ctx['interval']}$.")
    return [l for l in lines if l]


def _sign_table_text(rows_meta, km):
    rows_meta = rows_meta or {}
    rows = rows_meta.get("rows", [])
    cols = rows_meta.get("cols", [])
    if not rows:
        return ""
    ncols = len(rows[0]["cols"])
    header = "x & " + " & ".join(cols) + " \\\\ \\hline"
    body = " \\\\ ".join(
        f"{r['label']} & " + " & ".join(c["val"] for c in r["cols"])
        for r in rows
    )
    return "$$\\begin{array}{c|" + ("c" * ncols) + "} " + header + " " + body + " \\end{array}$$"


def _sl_parity(ctx, var, fn, G):
    km = G is KHMER
    fn = ctx.get("fn", fn)
    split = _ln(ctx.get("split", ""))
    P, Q = ctx.get("P", "?"), ctx.get("Q", "?")
    lines = [
        f"គេមាន ${split}$" if km else f"We have ${split}$",
        f"គេបាន $g(-x) = \\ln({Q}) - \\ln({P}) = -[\\ln({P}) - \\ln({Q})] = -g(x)$" if km
        else f"We get $g(-x) = \\ln({Q}) - \\ln({P}) = -[\\ln({P}) - \\ln({Q})] = -g(x)$",
        f"ម្យ៉ាងទៀត $g(-x) = \\ln\\left(\\frac{{{Q}}}{{{P}}}\\right) = \\ln\\left(\\frac{{{P}}}{{{Q}}}\\right)^{{-1}} = -g(x)$" if km
        else f"Also $g(-x) = \\ln\\left(\\frac{{{Q}}}{{{P}}}\\right) = -\\ln\\left(\\frac{{{P}}}{{{Q}}}\\right) = -g(x)$",
    ]
    key = {"odd": "is_odd", "even": "is_even", "neither": "is_neither"}.get(ctx.get("verdict"), "is_neither")
    lines.append(f"ដូច្នេះ ${fn}$ {G[key]} ។" if km else f"Therefore ${fn}$ {G[key]}.")
    return lines


def _sl_limit(ctx, var, fn, G):
    km = G is KHMER
    fn = ctx.get("fn", fn)
    point = ctx.get("point", "")
    side = ctx.get("side", "")
    sgn = "+" if side == "+" else ("-" if side == "-" else "")
    arg = _ln(ctx.get("arg", "?"))
    behavior = ctx.get("behavior", "")
    val = ctx.get("value_latex", "")
    if behavior:
        inner = f"\\left(\\frac{{{behavior}}}{{}}\\right)"  # placeholders removed below
        return [
            f"$\\lim_{{{var}\\to {point}^{sgn}}} {fn}(x) = \\lim_{{{var}\\to {point}^{sgn}}} \\ln({arg}) "
            f"= \\ln({behavior}) = \\ln 0^{{+}} = {val}$" if km
            else f"$\\lim_{{{var}\\to {point}^{sgn}}} {fn}(x) = \\ln({arg}) "
                 f"= \\ln({behavior}) = {val}$"
        ]
    return [
        f"$\\lim_{{{var}\\to {point}^{sgn}}} {fn}(x) = {val}$" if km
        else f"$\\lim_{{{var}\\to {point}^{sgn}}} {fn}(x) = {val}$"
    ]


def _sl_derivative(ctx, var, fn, G):
    km = G is KHMER
    split = _ln(ctx.get("split", ""))
    P, Q = ctx.get("P", "?"), ctx.get("Q", "?")
    dP, dQ = ctx.get("dP", "?"), ctx.get("dQ", "?")
    der = _ln(ctx.get("expr", "?"))
    return [
        f"${split}$" if km else f"${split}$",
        f"គេបាន $g'({var}) = \\frac{{{dP}}}{{{P}}} - \\frac{{{dQ}}}{{{Q}}} = {der}$" if km
        else f"We get $g'({var}) = \\frac{{{dP}}}{{{P}}} - \\frac{{{dQ}}}{{{Q}}} = {der}$",
    ]


def _sl_monotonicity(ctx, var, fn, G):
    km = G is KHMER
    fn = ctx.get("fn", fn)
    der = ctx.get("der", "?")
    pieces = ctx.get("pieces", [])
    out = []
    for p in pieces:
        w = _D[p["direction"]] if km else _D_EN[p["direction"]]
        out.append(f"ដូច្នេះ ${fn}$ កើន ${p['interval']}$ ។" if km else f"Therefore ${fn}$ is {w} on ${p['interval']}$.")
    return out or ["ថេរ ។" if km else "constant."]


def _sl_tangent(ctx, var, fn, G):
    km = G is KHMER
    fn = ctx.get("fn", fn)
    x0 = ctx.get("x0", "0")
    y0 = ctx.get("y0", "?")
    m = ctx.get("m", "?")
    line = ctx.get("line", "?")
    return [
        f"ដោយ $x_0 = {x0}$" if km else f"With $x_0 = {x0}$",
        f"$y_0 = {fn}({x0}) = {y0}$" if km else f"$y_0 = {fn}({x0}) = {y0}$",
        f"${fn}'({x0}) = {m}$" if km else f"${fn}'({x0}) = {m}$",
        f"$T: y - y_0 = {fn}'({x0})(x - x_0) \\Rightarrow y = {line}$" if km
        else f"$T: y - y_0 = {fn}'({x0})(x - x_0) \\Rightarrow y = {line}$",
        f"ដូច្នេះ $y = {line}$ ។" if km else f"Therefore $y = {line}$.",
    ]


def _sl_sign(ctx, var, fn, G):
    km = G is KHMER
    fn = ctx.get("fn", fn)
    neg = ctx.get("neg", "∅")
    pos = ctx.get("pos", "∅")
    return [
        f"ចំពោះ $x \\in {neg}$ គេបាន ${fn}({var}) < 0$" if km
        else f"For $x \\in {neg}$ we have ${fn}({var}) < 0$",
        f"ចំពោះ $x \\in {pos}$ គេបាន ${fn}({var}) > 0$" if km
        else f"For $x \\in {pos}$ we have ${fn}({var}) > 0$",
    ]


def _sl_derivative_product(ctx, var, fn, G):
    km = G is KHMER
    h = ctx.get("h_fn", "h")
    g = _ln(ctx.get("g", "?"))
    gp = _ln(ctx.get("gprime", "?"))
    der = _ln(ctx.get("expr", "?"))
    return [
        f"ដោយ $h({var}) = {var}{fn}({var})$" if km else f"With $h({var}) = {var}{fn}({var})$",
        f"$h'({var}) = {fn}({var}) + {var}{fn}'({var})$" if km else f"$h'({var}) = {fn}({var}) + {var}{fn}'({var})$",
        f"$= {g} + {var}({gp})$" if km else f"$= {g} + {var}({gp})$",
        f"$= {der}$" if km else f"$= {der}$",
    ]


def _sl_integral(ctx, var, fn, G):
    km = G is KHMER
    fn = ctx.get("fn", fn)
    h = ctx.get("h", "?")
    lower, upper = ctx.get("lower", "0"), ctx.get("upper", "1")
    val = _ln(ctx.get("value", "?"))
    g = _ln(ctx.get("g", "?"))
    gp = _ln(ctx.get("gprime", "?"))
    return [
        f"ដោយ $h'({var}) = {fn}({var}) + {var}{fn}'({var})$" if km
        else f"With $h'({var}) = {fn}({var}) + {var}{fn}'({var})$",
        f"${fn}({var}) = h'({var}) - {var}{fn}'({var})$" if km
        else f"${fn}({var}) = h'({var}) - {var}{fn}'({var})$",
        f"គេបាន $S = \\int_{{{lower}}}^{{{upper}}} {fn}({var})\\,dx$" if km
        else f"We have $S = \\int_{{{lower}}}^{{{upper}}} {fn}({var})\\,dx$",
        f"$= [h({var})]_{{{lower}}}^{{{upper}}} = {val}$ ឯកតាផ្ទៃ" if km
        else f"$= [h({var})]_{{{lower}}}^{{{upper}}} = {val}$ square units",
    ]


def _sl_variation_table(ctx, var, fn, G):
    km = G is KHMER
    return [f"{G['variation_table']} ។" if km else f"{G['variation_table']}."]


def _sl_draw(ctx, var, fn, G):
    km = G is KHMER
    return [f"{G['draw']} C {G['with']} {G['tangent']} T ។" if km
            else f"{G['draw']} C {G['with']} the {G['tangent']} T."]


_LOG_STEP_TEMPLATES = {
    "domain": _sl_domain,
    "parity": _sl_parity,
    "limit": _sl_limit,
    "derivative": _sl_derivative,
    "monotonicity": _sl_monotonicity,
    "tangent": _sl_tangent,
    "sign": _sl_sign,
    "derivative_product": _sl_derivative_product,
    "integral": _sl_integral,
    "variation_table": _sl_variation_table,
    "draw": _sl_draw,
}


# ---------- generic fallback (rational / other shapes) ----------
def _s_domain(ctx, var, fn, G):
    lines = []
    if ctx.get("interval"):
        lines.append(
            f"{G['domain']} D = {ctx['interval']} ។" if G is KHMER
            else f"{G['domain']} D = {ctx['interval']}."
        )
    return lines


def _s_parity(ctx, var, fn, G):
    key = {"odd": "is_odd", "even": "is_even", "neither": "is_neither"}.get(ctx.get("verdict"), "is_neither")
    return [
        f"{fn}(-{var}) + {fn}({var}) = 0 ។" if G is KHMER else f"{fn}(-{var}) + {fn}({var}) = 0.",
        f"{G['therefore']} {fn} {G[key]} ។" if G is KHMER else f"{G['therefore']} {fn} {G[key]}.",
    ]


def _s_limit(ctx, var, fn, G):
    side = ctx.get("side")
    sgn = "+" if side == "+" else ("-" if side == "-" else "")
    value = ctx.get("value_latex") if ctx.get("infinite") else str(ctx.get("value"))
    return [
        f"lim{{x→{ctx.get('point')}{sgn}}} {fn}(x) = {value} ។" if G is KHMER
        else f"lim{{x→{ctx.get('point')}{sgn}}} {fn}(x) = {value}.",
    ]


def _s_limits(ctx, var, fn, G):
    out = []
    for r in ctx.get("results", []):
        out.append(f"lim{{x→{r['point']}}} {fn}(x) = {r['value']} ។" if G is KHMER
                   else f"lim{{x→{r['point']}}} {fn}(x) = {r['value']}.")
    return out


def _s_derivative(ctx, var, fn, G):
    expr = ctx.get("expr_latex") or ctx.get("expr") or ""
    return [
        f"{G['we_get']} {fn}'({var}) = {expr} ។" if G is KHMER else f"{G['we_get']} {fn}'({var}) = {expr}.",
    ]


def _s_monotonicity(ctx, var, fn, G):
    pieces = []
    for p in ctx.get("pieces", []):
        word = _DIRECTION_KM[p["direction"]] if G is KHMER else _DIRECTION_EN[p["direction"]]
        pieces.append(f"{word} {G['on']} {p['interval']}")
    joined = " ".join(pieces) or G["constant"]
    if G is KHMER:
        return [f"{G['therefore']} {fn} {joined} ។"]
    return [f"{G['therefore']} {fn} is {', '.join(pieces) or G['constant']}."]


def _s_sign(ctx, var, fn, G):
    neg = ctx.get("neg") or "∅"
    pos = ctx.get("pos") or "∅"
    return [
        f"{fn}({var}) < 0 {G['on']} {neg} ; {fn}({var}) > 0 {G['on']} {pos} ។" if G is KHMER
        else f"{fn}({var}) < 0 {G['on']} {neg} ; {fn}({var}) > 0 {G['on']} {pos}.",
    ]


def _s_variation_table(ctx, var, fn, G):
    return [f"{G['variation_table']} ។" if G is KHMER else f"{G['variation_table']}."]


def _s_tangent(ctx, var, fn, G):
    y0, m = ctx.get("y0"), ctx.get("m")
    line = ctx.get("line_latex") or ctx.get("line") or ""
    lines = []
    if y0 is not None:
        lines.append(f"{fn}({ctx.get('x0')}) = {y0} ។" if G is KHMER else f"{fn}({ctx.get('x0')}) = {y0}.")
    if m is not None:
        lines.append(f"{fn}'({ctx.get('x0')}) = {m} ។" if G is KHMER else f"{fn}'({ctx.get('x0')}) = {m}.")
    lines.append(f"{G['tangent_eq']} T: y = {line} ។" if G is KHMER
                 else f"{G['tangent_eq']} T: y = {line}.")
    return lines


def _s_draw(ctx, var, fn, G):
    return [
        f"{G['draw']} C {G['with']} {G['tangent']} T ។" if G is KHMER
        else f"{G['draw']} C {G['with']} the {G['tangent']} T."
    ]


def _s_derivative_product(ctx, var, fn, G):
    h = ctx.get("h_fn") or "h"
    expr = ctx.get("expr_latex") or ctx.get("expr") or ""
    return [
        f"{G['we_get']} {h}'({var}) = {expr} ។" if G is KHMER else f"{G['we_get']} {h}'({var}) = {expr}.",
    ]


def _s_integral(ctx, var, fn, G):
    value = ctx.get("value_latex") or str(ctx.get("value") or "")
    return [
        f"{G['we_get']} S = {value} {G['square_units']} ។" if G is KHMER
        else f"{G['we_get']} S = {value} {G['square_units']}.",
    ]


def _s_asymptote(ctx, var, fn, G):
    line = ctx.get("line_latex") or ctx.get("line") or ""
    kind = ctx.get("kind", "oblique")
    key = f"asymptote_{kind}"
    label = G.get(key, G["asymptote_oblique"])
    return [
        f"{G['therefore']} {label} y = {line} ។" if G is KHMER
        else f"{G['therefore']} the {label} is y = {line}."
    ]


def _s_decompose(ctx, var, fn, G):
    dec = ctx.get("dec_latex") or ctx.get("dec") or ""
    a, b, c = ctx.get("a"), ctx.get("b"), ctx.get("c")
    lines = [f"{fn}({var}) = {dec} ។" if G is KHMER else f"{fn}({var}) = {dec}."]
    if None not in (a, b, c):
        lines.append(f"a={a}, b={b}, c={c} ។" if G is KHMER else f"a={a}, b={b}, c={c}.")
    return lines


def _s_position(ctx, var, fn, G):
    above = ctx.get("above") or "∅"
    below = ctx.get("below") or "∅"
    return [
        f"C {G['above']} d {G['on']} {above} ; C {G['below']} d {G['on']} {below} ។" if G is KHMER
        else f"C {G['above']} d {G['on']} {above} ; C {G['below']} d {G['on']} {below}."
    ]


def _s_symmetry(ctx, var, fn, G):
    if ctx.get("center"):
        return [
            f"I {G['center_symmetry']} of C ។" if G is KHMER else f"I {G['center_symmetry']} of C."
        ]
    return [
        "I មិនមែនជាចំណុចកណ្ដាលស៊ីមេទ្រីរបស់ C ។" if G is KHMER
        else "I is not the center of symmetry of C."
    ]


_STEP_TEMPLATES = {
    "domain": _s_domain,
    "parity": _s_parity,
    "limit": _s_limit,
    "limits": _s_limits,
    "derivative": _s_derivative,
    "monotonicity": _s_monotonicity,
    "sign": _s_sign,
    "variation_table": _s_variation_table,
    "tangent": _s_tangent,
    "draw": _s_draw,
    "derivative_product": _s_derivative_product,
    "integral": _s_integral,
    "asymptote": _s_asymptote,
    "decompose": _s_decompose,
    "position": _s_position,
    "symmetry": _s_symmetry,
}


def render_steps(want, ctx, var="x", fn="f", lang="km"):
    """Return the step-narrative lines for a want from its structured ctx.
    Log-shaped functions use the mirror-the-2025 templates; everything else uses
    the generic registry."""
    G = KHMER if lang == "km" else EN
    shape = ctx.get("shape")
    tpl = (_LOG_STEP_TEMPLATES if shape == "log" else _STEP_TEMPLATES).get(want)
    if tpl is None:
        return []
    try:
        lines = tpl(ctx, var, fn, G)
        if isinstance(lines, str):
            lines = [lines]
        return lines
    except Exception:
        return []



# --- English question templates (for the modal's English view) ---------------
def _q_domain(ctx, var, fn):
    return f"Find the domain of {fn}."


def _q_parity(ctx, var, fn):
    return f"Determine whether {fn} is even or odd."


def _q_limit(ctx, var, fn):
    side = ctx.get("side")
    sgn = "+" if side == "+" else ("-" if side == "-" else "")
    return f"Compute the limit of {fn} at {ctx['point']}{sgn}."


def _q_limits(ctx, var, fn):
    return f"Compute the limits of {fn} at the given points."


def _q_derivative(ctx, var, fn):
    return f"Compute the derivative {fn}'({var})."


def _q_monotonicity(ctx, var, fn):
    return f"Study the monotonicity of {fn} over its domain."


def _q_sign(ctx, var, fn):
    return f"Study the sign of {fn}({var}) according to {var}."


def _q_variation_table(ctx, var, fn):
    return f"Build the variation table of {fn}."


def _q_tangent(ctx, var, fn):
    return f"Find the equation of the tangent line T to C at the point of abscissa {ctx.get('x0')}."


def _q_draw(ctx, var, fn):
    return f"Draw the graph C and the tangent line T."


def _q_derivative_product(ctx, var, fn):
    h = ctx.get("h_fn") or "h"
    return f"Compute the derivative of {h} defined by {h}({var}) = {var} {fn}({var})."


def _q_integral(ctx, var, fn):
    return (f"Find the area of the region bounded by C, the x-axis, and the lines "
            f"{var} = {ctx.get('lower')} and {var} = {ctx.get('upper')}.")


def _q_asymptote(ctx, var, fn):
    kind = ctx.get("kind", "oblique")
    return f"Show that the line y = {ctx['line']} is the {kind} asymptote of C."


def _q_decompose(ctx, var, fn):
    return f"Find the real numbers a, b, c such that {fn}({var}) = a{var} + b + c/(...)."


def _q_position(ctx, var, fn):
    return f"Study the position of C relative to the line d."


def _q_symmetry(ctx, var, fn):
    return f"Determine whether I is the center of symmetry of C."


_QUESTION_TEMPLATES = {
    "domain": _q_domain,
    "parity": _q_parity,
    "limit": _q_limit,
    "limits": _q_limits,
    "derivative": _q_derivative,
    "monotonicity": _q_monotonicity,
    "sign": _q_sign,
    "variation_table": _q_variation_table,
    "tangent": _q_tangent,
    "draw": _q_draw,
    "derivative_product": _q_derivative_product,
    "integral": _q_integral,
    "asymptote": _q_asymptote,
    "decompose": _q_decompose,
    "position": _q_position,
    "symmetry": _q_symmetry,
}


def render_question(want, ctx, var="x", fn="f"):
    """English question sentence for a want (the Khmer question comes from the
    exercise's own ``question_km``). Returns ``None`` if no template exists."""
    tpl = _QUESTION_TEMPLATES.get(want)
    if tpl is None:
        return None
    try:
        return tpl(ctx, var, fn)
    except Exception:
        return None