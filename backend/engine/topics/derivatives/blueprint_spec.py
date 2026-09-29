"""What an LLM needs to write, and SymPy needs to check, a derivatives
blueprint (see ``engine/core/blueprints.py`` for the format and the
validation gate). Consumed by ``scripts/generate_blueprints.py``."""
import re

from sympy import diff, simplify

from .structures import instantiate, slot_names

TOPIC = "derivatives"
FORMULA = "compute_derivative"


def truth(struct, y, x):
    """The final answer — the solver's own rule, never the blueprint's."""
    return simplify(diff(y, x, struct["order"]))


def required(struct, bp, values, x, y, final):
    """A second-derivative blueprint must make the student show y'."""
    if struct["order"] == 2:
        first = diff(y, x)
        if not any(simplify(v - first) == 0 for _, v in values["checkpoints"]):
            return ["second-derivative blueprint has no checkpoint equal to y'"]
    return []


def validate(bp, struct, samples=6, seed=0):
    from ...core import blueprints

    return blueprints.validate(bp, struct, instantiate, truth, samples=samples, seed=seed, required=required)


def template_brief(struct):
    """How one template is presented to the LLM."""
    return {
        "template_id": struct["id"],
        "function": "y = " + re.sub(r"\{(\w+)\}", r"\1", struct["pattern"]),
        "slots": slot_names(struct),
        "find": "y''" if struct["order"] == 2 else "y'",
        "main_rule": struct["rule"],
    }


_STRING = {"type": "STRING"}

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "templates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "template_id": _STRING,
                    "definitions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {"name": _STRING, "expr": _STRING},
                            "required": ["name", "expr"],
                        },
                    },
                    "compose": _STRING,
                    "checkpoints": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "id": _STRING,
                                "relation": {"type": "STRING", "enum": ["derivative", "outer_derivative", "combination"]},
                                "of": _STRING,
                                "outer": _STRING,
                                "at": _STRING,
                                "equals": _STRING,
                                "expr": _STRING,
                                "label_en": _STRING,
                                "label_km": _STRING,
                            },
                            "required": ["id", "relation", "of", "outer", "at", "equals", "expr", "label_en", "label_km"],
                        },
                    },
                },
                "required": ["template_id", "definitions", "compose", "checkpoints"],
            },
        }
    },
    "required": ["templates"],
}

PROMPT = r"""You are a senior Grade 12 Cambodian BAC II mathematics examiner writing the official
MARKING SCHEME for derivative exercises. Each exercise below is a TEMPLATE: a function y of x
with integer parameters (slots). Write one blueprint per template that works for ANY slot values.

A blueprint names the pieces of y (definitions) and lists the intermediate results a marker
awards points for (checkpoints), in the order a student writes them. You are NOT computing a
numeric answer; a computer algebra system will recompute and verify everything you write.

EXPRESSION SYNTAX (strict, SymPy):
- x is the variable. Slots are plain symbols (a, b, k, ...). Use * for every product, ** for powers.
- exp(...) for e^..., log(...) for ln, sqrt(...), sin, cos, tan. Never write e as a number.

DEFINITIONS: named sub-expressions of y, e.g. u = a*x + b, v = exp(k*x).
- Names: u, v, w, g, h (never a slot name, x, y or t).
- "compose": an expression in the definition names that rebuilds y exactly (e.g. "u*v", "u/v",
  "u**n", "log(u/v)"). If you use no definitions, set compose to "" and definitions to [].

CHECKPOINTS: each has an id (short identifier, e.g. u_p, v_p, num, y1), a relation, and expr.
- relation "derivative": the derivative with respect to x of `of`, where `of` is an expression
  in definition names, earlier checkpoint ids or y (e.g. "u", "log(v)", "y", "y1").
- relation "outer_derivative": chain rule's outer part: `outer` is the outer function written in
  the letter t (e.g. "t**n", "sqrt(t)", "sin(t)", "log(t)") and `at` is where it is evaluated
  (e.g. "u"). Value = outer'(t) with t replaced by `at`.
- relation "combination": `equals` is an expression in definition names / earlier checkpoint ids
  (e.g. "u_p*v - u*v_p", the numerator of the quotient rule).
- Unused fields of a checkpoint are "".
- expr: YOUR explicit value of that checkpoint, written ONLY in x and the slots (no definition
  names). It is checked against the computer algebra system on random slot values.
- label_en / label_km: short labels, e.g. "u'", "v'", "numerator u'v - uv'", "y'"; label_km is
  the Khmer label (keep the math notation, e.g. "ដេរីវេ u'").

MARKING RULES:
1. Only intermediate results. NEVER include the final answer, and NEVER include anything that
   is mathematically equal to y or to the final answer (for example u'v + uv' before simplifying
   IS the final answer — leave it out). Every checkpoint must have a different value.
2. No checkpoint that is always 0 (e.g. the derivative of a constant numerator): it earns no
   marks. 1 to 5 checkpoints; pick the ones a real marker gives points for (u', v', the inner
   derivative, the outer derivative, the quotient-rule numerator, each term's derivative).
3. If y'' is asked, include y' itself as a checkpoint (relation "derivative", of "y").
4. A plain polynomial differentiated term by term may have [] checkpoints if no intermediate
   result is distinct from the answer.

EXAMPLES:

Template: y = (a*x + b)*exp(k*x), find y', slots [a, b, k]
{"template_id": "deriv:exponential:linear_times_exp",
 "definitions": [{"name": "u", "expr": "a*x + b"}, {"name": "v", "expr": "exp(k*x)"}],
 "compose": "u*v",
 "checkpoints": [
  {"id": "u_p", "relation": "derivative", "of": "u", "outer": "", "at": "", "equals": "", "expr": "a", "label_en": "u'", "label_km": "ដេរីវេ u'"},
  {"id": "v_p", "relation": "derivative", "of": "v", "outer": "", "at": "", "equals": "", "expr": "k*exp(k*x)", "label_en": "v'", "label_km": "ដេរីវេ v'"}]}

Template: y = (a*x**2 + c*x + b)**n, find y', slots [a, b, c, n]
{"template_id": "deriv:chain:quadratic_power",
 "definitions": [{"name": "u", "expr": "a*x**2 + c*x + b"}],
 "compose": "u**n",
 "checkpoints": [
  {"id": "u_p", "relation": "derivative", "of": "u", "outer": "", "at": "", "equals": "", "expr": "2*a*x + c", "label_en": "u'", "label_km": "ដេរីវេ u'"},
  {"id": "outer_p", "relation": "outer_derivative", "of": "", "outer": "t**n", "at": "u", "equals": "", "expr": "n*(a*x**2 + c*x + b)**(n - 1)", "label_en": "n·u^(n-1)", "label_km": "n·u^(n-1)"}]}

Template: y = (a*x + b)/(c*x + d), find y', slots [a, b, c, d]
{"template_id": "deriv:quotient:linear_over_linear",
 "definitions": [{"name": "u", "expr": "a*x + b"}, {"name": "v", "expr": "c*x + d"}],
 "compose": "u/v",
 "checkpoints": [
  {"id": "u_p", "relation": "derivative", "of": "u", "outer": "", "at": "", "equals": "", "expr": "a", "label_en": "u'", "label_km": "ដេរីវេ u'"},
  {"id": "v_p", "relation": "derivative", "of": "v", "outer": "", "at": "", "equals": "", "expr": "c", "label_en": "v'", "label_km": "ដេរីវេ v'"},
  {"id": "num", "relation": "combination", "of": "", "outer": "", "at": "", "equals": "u_p*v - u*v_p", "expr": "a*(c*x + d) - c*(a*x + b)", "label_en": "numerator u'v - uv'", "label_km": "ភាគយក u'v - uv'"}]}

Template: y = log((a*x + b)/(c*x + d)), find y', slots [a, b, c, d]
{"template_id": "deriv:logarithm:log_of_quotient",
 "definitions": [{"name": "u", "expr": "a*x + b"}, {"name": "v", "expr": "c*x + d"}],
 "compose": "log(u/v)",
 "checkpoints": [
  {"id": "d1", "relation": "derivative", "of": "log(u)", "outer": "", "at": "", "equals": "", "expr": "a/(a*x + b)", "label_en": "(ln u)'", "label_km": "ដេរីវេ ln u"},
  {"id": "d2", "relation": "derivative", "of": "log(v)", "outer": "", "at": "", "equals": "", "expr": "c/(c*x + d)", "label_en": "(ln v)'", "label_km": "ដេរីវេ ln v"}]}

Template: y = (a*x + b)*exp(c*x), find y'', slots [a, b, c]
{"template_id": "deriv:second_order:linear_times_exp",
 "definitions": [{"name": "u", "expr": "a*x + b"}, {"name": "v", "expr": "exp(c*x)"}],
 "compose": "u*v",
 "checkpoints": [
  {"id": "u_p", "relation": "derivative", "of": "u", "outer": "", "at": "", "equals": "", "expr": "a", "label_en": "u'", "label_km": "ដេរីវេ u'"},
  {"id": "v_p", "relation": "derivative", "of": "v", "outer": "", "at": "", "equals": "", "expr": "c*exp(c*x)", "label_en": "v'", "label_km": "ដេរីវេ v'"},
  {"id": "y1", "relation": "derivative", "of": "y", "outer": "", "at": "", "equals": "", "expr": "a*exp(c*x) + c*(a*x + b)*exp(c*x)", "label_en": "y'", "label_km": "ដេរីវេទី១ y'"}]}

Return JSON {"templates": [...]} with exactly one blueprint per template below, same template_id.

TEMPLATES:
"""


def alternative_brief(struct, standard):
    """A template plus its validated standard method, for --alternatives."""
    return {
        **template_brief(struct),
        "standard_method": {k: standard.get(k) for k in ("definitions", "compose", "checkpoints")},
    }


_METHOD_ITEM = {
    "type": "OBJECT",
    "properties": {
        "method_id": _STRING,
        "name_en": _STRING,
        "name_km": _STRING,
        **RESPONSE_SCHEMA["properties"]["templates"]["items"]["properties"],
    },
    "required": ["method_id", "name_en", "name_km", "definitions", "compose", "checkpoints"],
}
_METHOD_ITEM["properties"].pop("template_id")

ALTERNATIVES_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "templates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"template_id": _STRING, "methods": {"type": "ARRAY", "items": _METHOD_ITEM}},
                "required": ["template_id", "methods"],
            },
        }
    },
    "required": ["templates"],
}

ALTERNATIVES_PROMPT = PROMPT[:PROMPT.index('Return JSON {"templates": [...]}')] + r"""
TASK FOR THIS REQUEST — ALTERNATIVE METHODS:
Each template below comes with its STANDARD method's blueprint ("standard_method"). Students
don't always use it. Write 0 to 2 ALTERNATIVE methods per template: other valid ways a real
Grade 12 BAC II student solves it, each as a complete blueprint in the same format, plus
method_id (snake_case, e.g. "expand_first", "chain_rule_on_quotient", "rewrite_as_power"),
name_en and name_km (a short name of the method).

Good alternatives: expanding/simplifying before differentiating; a different choice of u and v;
splitting a logarithm vs. the chain rule on the whole argument (or the reverse); rewriting a
quotient as a product with a negative power; the quotient rule vs. rewriting as a power; the
product rule vs. expanding. An alternative must ask for DIFFERENT intermediate results than the
standard method — renaming u and v, or the same steps in another order, is NOT an alternative.
Every marking rule above still applies to each alternative (no checkpoint equal to y or to the
final answer; at least one checkpoint). If no genuinely different method exists, return
"methods": [].

Return JSON {"templates": [{"template_id": ..., "methods": [...]}, ...]}, one entry per template.

TEMPLATES:
"""


def structures():
    from .structures import all_derivative_structures

    return all_derivative_structures()
