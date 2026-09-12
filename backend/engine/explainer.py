"""Step-by-step explanation.

`build_text()` produces a deterministic explanation directly from SymPy's steps
(always available), in English or Khmer. `explain()` optionally asks an LLM
(Gemini, then Ollama) to rewrite those steps in friendlier language; the LLM
never invents new math.
"""
import re

from sympy import I, Symbol, sympify

from engine import llm
from engine.solver import _calc_locals, inline_latex, solve


def _safe_expr(raw, var):
    """LaTeX for a curated expression string, or "" when it will not parse.

    The curated exam topics store their expressions as free text, so a single
    unparseable entry must degrade to a plainer description rather than break
    the whole explanation.
    """
    if not raw:
        return ""
    try:
        return inline_latex(sympify(raw, locals=_calc_locals(var)))
    except Exception:
        return ""


def _complex_given(question_type, params):
    """Describe the "given" of a complex question as (kind, pieces).

    Each complex template carries its own parameter shape — only the five
    single-number types (modulus/argument/conjugate/real_part/imaginary_part)
    have a plain ``a``/``b`` pair, while the arithmetic, power, De Moivre and
    n-th root templates store operands or polar coordinates instead. Reading
    ``params["a"]`` unconditionally raised ``KeyError`` on four of the nine
    types, so both problem descriptions go through this one reader.
    """
    if question_type == "complex_arithmetic":
        z1 = params["a1"] + params["b1"] * I
        z2 = params["a2"] + params["b2"] * I
        return "pair", (inline_latex(z1), inline_latex(z2), params.get("operation"))
    if question_type == "complex_power":
        return "power", (inline_latex(params["a"] + params["b"] * I), params["n"])
    if question_type in ("de_moivre_power", "nth_roots"):
        from sympy import cos, sin, simplify

        from engine.topics.complex.trig import angle_from, principal_kd, z_from_polar

        if question_type == "de_moivre_power":
            z = z_from_polar(params["r"], params["k"], params["d"])
            return "power", (inline_latex(z), params["n"])
        # nth_roots stores the *answer* w in polar form; the given z is w^n.
        rho, k0, d0, n = params["rho"], params["k0"], params["d0"], params["n"]
        zk, zd = principal_kd(k0 * n, d0)
        theta = angle_from(zk, zd)
        z = simplify(rho ** n * cos(theta) + rho ** n * I * sin(theta))
        return "root", (inline_latex(z), n)
    if "a" in params and "b" in params:
        return "single", (inline_latex(params["a"] + params["b"] * I),)
    return "unknown", ()


_COMPLEX_OP_EN = {"add": "sum", "subtract": "difference", "multiply": "product", "divide": "quotient"}
_COMPLEX_OP_KM = {"add": "ផលបូក", "subtract": "ផលដក", "multiply": "ផលគុណ", "divide": "ផលចែក"}

_COMPLEX_QTYPE_KM = {
    "modulus": "ម៉ូឌុល",
    "argument": "អាគុយម៉ង់",
    "conjugate": "ចំនួនកុំផ្លិចឆ្លាស់",
    "real_part": "ផ្នែកពិត",
    "imaginary_part": "ផ្នែកនិម្មិត",
}


def _problem_desc(topic, question_type, params):
    if topic == "complex":
        kind, pieces = _complex_given(question_type, params)
        if kind == "pair":
            z1, z2, op = pieces
            return f"{_COMPLEX_OP_EN.get(op, op or 'operation')} of \\(z_1\\) = {z1} and \\(z_2\\) = {z2}"
        if kind == "power":
            z, n = pieces
            return f"\\(z^{{{n}}}\\) for \\(z\\) = {z}"
        if kind == "root":
            z, n = pieces
            return f"an \\(n\\)-th root \\(w\\) with \\(w^{{{n}}}\\) = {z}"
        if kind == "single":
            return f"{question_type} of \\(z\\) = {pieces[0]}"
        return f"{question_type} with {params}"
    if topic == "limit":
        var = params["var"]
        expr = sympify(params["expr"], locals=_calc_locals(var))
        point = sympify(params["point"], locals=_calc_locals(var))
        return f"limit of {inline_latex(expr)} as \\({var} \\to {point}\\)"
    if topic == "integral":
        var = params["var"]
        expr = sympify(params["expr"], locals=_calc_locals(var))
        if question_type == "indefinite_integral":
            return f"indefinite integral of {inline_latex(expr)} with respect to \\({var}\\)"
        lower = sympify(params["lower"], locals=_calc_locals(var))
        upper = sympify(params["upper"], locals=_calc_locals(var))
        return f"integral of {inline_latex(expr)} \\(d{var}\\) from \\({var} = {lower}\\) to \\({var} = {upper}\\)"
    if topic == "probability":
        structure = params.get("structure", "?")
        want = params.get("want")
        label = f"{structure}" + (f" ({want})" if want else "")
        return f"probability word problem ({label})"
    if topic == "functions":
        var = params.get("var", "x")
        expr = sympify(params.get("function_expr"), locals=_calc_locals(var))
        return f"function study of {inline_latex(expr)}"
    if topic == "derivatives":
        var = params.get("var", "x")
        expr = _safe_expr(params.get("expr"), var)
        order = "second derivative" if params.get("order") == 2 else "derivative"
        return f"{order} of \\(y\\) = {expr}" if expr else order
    if topic == "continuity":
        var = params.get("var", "x")
        at = f" at \\({var} = {params['point']}\\)" if params.get("point") is not None else ""
        if params.get("unknown"):
            return f"the value of \\({params['unknown']}\\) making the piecewise function continuous{at}"
        return f"continuity of the piecewise function{at}"
    if topic == "conics":
        expr = _safe_expr(params.get("expr"), "x")
        ask = params.get("ask")
        what = f" ({ask})" if ask else ""
        return f"conic {expr} = 0{what}" if expr else f"conic study{what}"
    if topic == "differential_equations":
        kind = str(params.get("kind", "")).replace("_", " ") or "differential equation"
        return f"differential equation ({kind})"
    if topic == "vectors_space":
        op = str(params.get("op", "")).replace("_", " ") or "vector operation"
        return f"vector operation in space ({op})"
    return f"{question_type} with {params}"


def _problem_desc_km(topic, question_type, params):
    if topic == "complex":
        kind, pieces = _complex_given(question_type, params)
        if kind == "pair":
            z1, z2, op = pieces
            return f"{_COMPLEX_OP_KM.get(op, 'ប្រមាណវិធី')}នៃ $z_1$ = {z1} និង $z_2$ = {z2}"
        if kind == "power":
            z, n = pieces
            return f"$z^{{{n}}}$ ដែល $z$ = {z}"
        if kind == "root":
            z, n = pieces
            return f"ឫសទី {n} គឺ $w$ ដែល $w^{{{n}}}$ = {z}"
        if kind == "single":
            return f"{_COMPLEX_QTYPE_KM.get(question_type, question_type)} នៃ $z$ = {pieces[0]}"
        return f"{question_type} ជាមួយ {params}"
    if topic == "limit":
        var = params["var"]
        expr = sympify(params["expr"], locals=_calc_locals(var))
        point = sympify(params["point"], locals=_calc_locals(var))
        return f"លីមីតនៃ {inline_latex(expr)} កាលណា ${var} \\to {point}$"
    if topic == "integral":
        var = params["var"]
        expr = sympify(params["expr"], locals=_calc_locals(var))
        if question_type == "indefinite_integral":
            return f"ព្រីមីទីវនៃ {inline_latex(expr)} ធៀបនឹង ${var}$"
        lower = sympify(params["lower"], locals=_calc_locals(var))
        upper = sympify(params["upper"], locals=_calc_locals(var))
        return f"អាំងតេក្រាលកំណត់នៃ {inline_latex(expr)} $d{var}$ ពី ${var} = {lower}$ ទៅ ${var} = {upper}$"
    if topic == "probability":
        structure = params.get("structure", "?")
        want = params.get("want")
        label = f"{structure}" + (f" ({want})" if want else "")
        return f"លំហាត់ប្រូបាប៊ីលីតេ ({label})"
    if topic == "functions":
        var = params.get("var", "x")
        expr = sympify(params.get("function_expr"), locals=_calc_locals(var))
        return f"សិក្សាអនុគមន៍ {inline_latex(expr)}"
    if topic == "derivatives":
        var = params.get("var", "x")
        expr = _safe_expr(params.get("expr"), var)
        order = "ដេរីវេទីពីរ" if params.get("order") == 2 else "ដេរីវេ"
        return f"{order}នៃ $y$ = {expr}" if expr else order
    if topic == "continuity":
        var = params.get("var", "x")
        at = f"ត្រង់ចំណុច ${var} = {params['point']}$" if params.get("point") is not None else ""
        if params.get("unknown"):
            return f"រកតម្លៃ ${params['unknown']}$ ដើម្បីឱ្យអនុគមន៍ជាប់{at}"
        return f"ភាពជាប់នៃអនុគមន៍{at}"
    if topic == "conics":
        expr = _safe_expr(params.get("expr"), "x")
        ask = params.get("ask")
        what = f" ({ask})" if ask else ""
        return f"កោនិក {expr} = 0{what}" if expr else f"សិក្សាកោនិក{what}"
    if topic == "differential_equations":
        kind = str(params.get("kind", "")).replace("_", " ") or ""
        return f"សមីការឌីផេរ៉ង់ស្យែល ({kind})" if kind else "សមីការឌីផេរ៉ង់ស្យែល"
    if topic == "vectors_space":
        op = str(params.get("op", "")).replace("_", " ") or ""
        return f"ប្រមាណវិធីលើវិចទ័រក្នុងលំហ ({op})" if op else "ប្រមាណវិធីលើវិចទ័រក្នុងលំហ"
    return f"{question_type} ជាមួយ {params}"


# Khmer wording for the step titles the solvers actually emit, keyed lowercase.
# Terminology follows each topic's data/formulas.json `name_km` so the step
# titles and the formula sheet name the same technique the same way.
_STEP_TITLE_KM = {
    # --- shared skeleton titles ---
    "apply the technique": "អនុវត្តវិធីសាស្ត្រ",
    "result": "លទ្ធផល",
    "result (algebraic form)": "លទ្ធផល (ទម្រង់ពីជគណិត)",
    "simplify": "សម្រួលកន្សោម",
    "substitute the values": "ជំនួសតម្លៃចូលក្នុងរូបមន្ត",
    "conclusion": "សន្និដ្ឋាន",
    "solve for the unknown": "ដោះស្រាយរកតម្លៃមិនស្គាល់",
    "evaluate": "គណនាតម្លៃ",
    "evaluate each": "គណនាម្តងមួយៗ",
    # --- complex numbers ---
    "identify z": "កំណត់ចំនួនកុំផ្លិច $z$",
    "identify the two numbers": "កំណត់ចំនួនកុំផ្លិចទាំងពីរ",
    "identify the real and imaginary parts": "កំណត់ផ្នែកពិត និងផ្នែកនិម្មិត",
    "identify the real part": "កំណត់ផ្នែកពិត",
    "identify the imaginary part": "កំណត់ផ្នែកនិម្មិត",
    "apply the modulus formula": "អនុវត្តរូបមន្តម៉ូឌុល",
    "apply the argument formula": "អនុវត្តរូបមន្តអាគុយម៉ង់",
    "apply the conjugate rule": "អនុវត្តច្បាប់ចំនួនកុំផ្លិចឆ្លាស់",
    "apply the sum rule": "អនុវត្តវិធីបូកចំនួនកុំផ្លិច",
    "apply the difference rule": "អនុវត្តវិធីដកចំនួនកុំផ្លិច",
    "apply the product rule": "អនុវត្តវិធីគុណចំនួនកុំផ្លិច",
    "apply the quotient rule": "អនុវត្តវិធីចែកចំនួនកុំផ្លិច",
    "write z in trigonometric form": "សរសេរ $z$ ជាទម្រង់ត្រីកោណមាត្រ",
    "apply de moivre's formula": "អនុវត្តរូបមន្តដឺម័រ (De Moivre)",
    "reduce the angle mod 2π": "បង្រួមមុំតាមម៉ូឌុយឡូ $2\\pi$",
    # --- limits ---
    "set up the limit": "តាំងលីមីត",
    "try direct substitution": "សាកល្បងជំនួសតម្លៃផ្ទាល់",
    "evaluate by direct substitution": "គណនាដោយជំនួសតម្លៃផ្ទាល់",
    "key identity used": "រូបមន្តគន្លឹះដែលប្រើ",
    "factor the expression": "ដាក់កន្សោមជាផលគុណកត្តា",
    "cancel the common factor": "សម្រួលកត្តារួម",
    "multiply and divide by the conjugate": "គុណ និងចែកនឹងកន្សោមឆ្លាស់",
    "apply the standard exponential limit": "អនុវត្តលីមីតគំរូអិចស្បូណង់ស្យែល",
    "divide numerator and denominator by the highest power": "ចែកភាគយក និងភាគបែងនឹងស្វ័យគុណខ្ពស់បំផុត",
    "divide numerator and denominator by the dominant power": "ចែកភាគយក និងភាគបែងនឹងស្វ័យគុណលេច",
    "divide numerator and denominator by the variable": "ចែកភាគយក និងភាគបែងនឹងអថេរ",
    "take the limit of the resulting ratio": "យកលីមីតនៃផលធៀបដែលទទួលបាន",
    # --- integrals ---
    "find the antiderivative": "រកព្រីមីទីវ",
    "apply the bounds": "អនុវត្តព្រំដែនអាំងតេក្រាល",
    "apply integration by parts": "អនុវត្តវិធីអាំងតេក្រាលដោយផ្នែក",
    "apply the linear-argument rule": "អនុវត្តរូបមន្តអថេរលីនេអ៊ែរ $ax+b$",
    "substitute u = g(x)": "ប្តូរអថេរ $u = g(x)$",
    "integrate in u": "គណនាអាំងតេក្រាលធៀបនឹង $u$",
    "integrate": "គណនាអាំងតេក្រាល",
    "rewrite the integrand": "សរសេរកន្សោមអាំងតេក្រាលឡើងវិញ",
    # --- derivatives ---
    "set up the derivative": "តាំងដេរីវេ",
    "first derivative": "ដេរីវេទីមួយ",
    "second derivative": "ដេរីវេទីពីរ",
    "derivative": "ដេរីវេ",
    "differentiate": "គណនាដេរីវេ",
    # --- continuity ---
    "set up the two one-sided limits": "តាំងលីមីតឆ្វេង និងលីមីតស្តាំ",
    "compute the limit(s) in terms of the unknown": "គណនាលីមីតតាមតម្លៃមិនស្គាល់",
    "compare the one-sided limits": "ប្រៀបធៀបលីមីតឆ្វេង និងលីមីតស្តាំ",
    "compute the limits": "គណនាលីមីត",
    # --- differential equations ---
    "set up the differential equation": "តាំងសមីការឌីផេរ៉ង់ស្យែល",
    # --- conics ---
    "complete the square": "បំពេញការេ",
    "classify and extract features": "កំណត់ប្រភេទ និងលក្ខណៈកោនិក",
    # --- vectors in space ---
    "build the vectors": "សង់វិចទ័រ",
    "compute the vector": "គណនាវិចទ័រ",
    "compute the magnitude": "គណនាប្រវែងវិចទ័រ",
    "compute its magnitude": "គណនាប្រវែងរបស់វា",
    "halve its magnitude": "យកពាក់កណ្តាលប្រវែងរបស់វា",
    "compute the dot product": "គណនាផលគុណស្កាលែ",
    "compute the cross product": "គណនាផលគុណវិចទ័រ",
    "compute v x w": "គណនា $\\vec{v} \\times \\vec{w}$",
    "dot with u": "គុណស្កាលែនឹង $\\vec{u}$",
    "compute the distance": "គណនាចម្ងាយ",
    "set up the orthogonality condition": "តាំងលក្ខខណ្ឌកែងគ្នា",
    # --- probability ---
    "count the total draws": "រាប់ចំនួនករណីអាចមានទាំងអស់",
    "count the favorable draws": "រាប់ចំនួនករណីស្រប",
    "count the unfavorable draws": "រាប់ចំនួនករណីមិនស្រប",
    "count the all-even draws": "រាប់ករណីដែលគ្រាប់ទាំងអស់ជាលេខគូ",
    "apply the ratio": "អនុវត្តផលធៀបប្រូបាប៊ីលីតេ",
    "apply the hypergeometric ratio": "អនុវត្តច្បាប់អុីពែរហ្សេអូម៉េទ្រិច",
    "apply the complement rule": "អនុវត្តច្បាប់ព្រឹត្តិការណ៍ផ្ទុយ",
    "multiply the independent draws": "គុណប្រូបាប៊ីលីតេនៃការទាញឯករាជ្យ",
    "probability from box 1": "ប្រូបាប៊ីលីតេពីប្រអប់ទី ១",
    "probability from box 2": "ប្រូបាប៊ីលីតេពីប្រអប់ទី ២",
    "probability that all drawn balls are even": "ប្រូបាប៊ីលីតេដែលគ្រាប់ទាញទាំងអស់ជាលេខគូ",
    "white from box 1, black from box 2": "ពណ៌សពីប្រអប់ទី ១ និងពណ៌ខ្មៅពីប្រអប់ទី ២",
    "black from box 1, white from box 2": "ពណ៌ខ្មៅពីប្រអប់ទី ១ និងពណ៌សពីប្រអប់ទី ២",
    "add the two disjoint cases": "បូកករណីមិនត្រួតគ្នាទាំងពីរ",
    # --- function study ---
    "domain of a logarithm": "ដែនកំណត់នៃអនុគមន៍លោការីត",
    "domain of a rational function": "ដែនកំណត់នៃអនុគមន៍សនិទាន",
    "denominator roots": "ឫសនៃភាគបែង",
    "locate the boundary points": "កំណត់ចំណុចព្រំដែន",
    "read the sign table": "អានតារាងសញ្ញា",
    "variation table": "តារាងអថេរភាព",
    "identify a, b, c": "កំណត់មេគុណ $a$, $b$, $c$",
    "polynomial division": "ចែកពហុធា",
    "quotient and remainder": "ផលចែក និងសំណល់",
    "rewrite using log rules": "សរសេរឡើងវិញដោយប្រើច្បាប់លោការីត",
    "compute g(-x)": "គណនា $g(-x)$",
    "find the horizontal asymptote": "រកអាស៊ីមតូតដេក",
    "find the oblique asymptote": "រកអាស៊ីមតូតទ្រេត",
    "difference with the line": "គណនាផលដកធៀបនឹងបន្ទាត់",
    "intercept": "ចំណុចប្រសព្វនឹងអ័ក្ស",
    "point of tangency": "ចំណុចប៉ះ",
    "slope of the tangent": "មេគុណប្រាប់ទិសនៃបន្ទាត់ប៉ះ",
    "equation of the tangent": "សមីការបន្ទាត់ប៉ះ",
    "draw the graph": "សង់ក្រាប",
    "translate to the candidate center": "ប្តូរទីតាំងទៅផ្ចិតឆ្លុះដែលសន្មត",
    "substitute g and g'": "ជំនួស $g$ និង $g'$",
}

# Titles that carry a rendered expression or a template number; matched only
# after the flat table misses, so a literal entry always wins.
_STEP_TITLE_KM_PATTERNS = [
    (re.compile(r"^Antiderivative of (.+)$"), "ព្រីមីទីវនៃ {0}"),
    (re.compile(r"^Expand z\^(\d+) algebraically$"), "ពន្លាត $z^{0}$ តាមពិជគណិត"),
    (re.compile(r"^Take the modulus\^\(1/(\d+)\) and divide the angle by \d+$"),
     "យកម៉ូឌុលស្វ័យគុណ $1/{0}$ រួចចែកអាគុយម៉ង់នឹង {0}"),
    (re.compile(r"^Limit at (.+)$"), "លីមីតត្រង់ {0}"),
    (re.compile(r"^Sign of (.+)$"), "សញ្ញានៃ {0}"),
]

_PART_PREFIX_RE = re.compile(r"^Part\s+([^:]+):\s*(.+)$")


def _step_title_km(title):
    """Khmer wording for one solver step title, or ``None`` when we have none.

    Titles arrive in three shapes: a fixed phrase ("Apply the bounds"), a
    part-prefixed phrase ("Part 2.a: Differentiate") and a phrase carrying a
    rendered expression ("Antiderivative of 5 x"). The part prefix is peeled
    off and translated separately so the base phrases stay one flat table.
    """
    raw = (title or "").strip()
    if not raw:
        return None
    prefix = ""
    part = _PART_PREFIX_RE.match(raw)
    if part:
        prefix = f"ផ្នែក {part.group(1)}៖ "
        raw = part.group(2).strip()
    km = _STEP_TITLE_KM.get(raw.lower())
    if km is None:
        for pattern, template in _STEP_TITLE_KM_PATTERNS:
            found = pattern.match(raw)
            if found:
                km = template.format(*found.groups())
                break
    if km is None:
        return None
    return prefix + km


def build_text(topic, question_type, params, solution, lang="en"):
    if lang == "km":
        from engine.formulas import resolve_formula

        lines = [f"ប្រធាន៖ {_problem_desc_km(topic, question_type, params)}។"]
        for i, step in enumerate(solution["steps"], 1):
            # Order matters: the step's own title is the specific one ("Set up
            # the derivative", "Result"), while the formula tag names only the
            # broad technique. Several topics tag every step of a solution with
            # one coarse tag, so consulting the tag first collapsed distinct
            # steps into the same repeated heading.
            km_title = step.get("title_km") or _step_title_km(step.get("title"))
            if not km_title and step.get("formula"):
                km_title = resolve_formula(step["formula"]).get("name_km")
            if not km_title:
                km_title = step.get("title", "")
            lines.append(f"ជំហានទី {i} ៖ {km_title}")
            lines.append(f"    {step['detail']}")
        lines.append(f"ចម្លើយ៖ {inline_latex(solution['answer_exact'])}")
        return "\n".join(lines)

    lines = [f"Problem: {_problem_desc(topic, question_type, params)}."]
    for i, step in enumerate(solution["steps"], 1):
        lines.append(f"Step {i}: {step['title']}")
        lines.append(f"    {step['detail']}")
    lines.append(f"Answer: {inline_latex(solution['answer_exact'])}")
    return "\n".join(lines)


async def explain(topic, question_type, params, use_ai=False, lang="en"):
    solution = solve(topic, question_type, params)
    steps_text = solution.get("solution_km") if lang == "km" and solution.get("solution_km") else build_text(topic, question_type, params, solution, lang=lang)
    ai = None
    if use_ai:
        ai, _ = await llm.narrate(steps_text, lang=lang)
    return {
        "question_type": question_type,
        "deterministic": steps_text,
        "ai": ai,
        "steps": solution["steps"],
        "answer": str(solution["answer_exact"]),
    }
