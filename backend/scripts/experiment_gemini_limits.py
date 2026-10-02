import asyncio
import json
import os
import re
from google.genai import types
from engine.llm import _gemini_generate

# Define the schema for batched template steps
BATCH_LIMIT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "templates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "template_id": {"type": "STRING"},
                    "indeterminate_form": {
                        "type": "STRING",
                        "description": "The exact indeterminate form: 0/0, 1^\\infty, \\infty/\\infty, or \\infty - \\infty"
                    },
                    "steps": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING",
                            "description": "A pure LaTeX equation line containing parameter placeholders like {a}, {b}, {k}. Line 1 MUST include the indeterminate form tag \\left(\\text{រាងមិនកំណត់ } ...\\right). Subsequent lines start with = \\lim_{...} or evaluate to the final algebraic form. ABSOLUTELY ZERO English or Khmer words permitted anywhere in the steps."
                        }
                    },
                    "checkpoints": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING",
                            "description": "The key intermediate mathematical expressions (right-hand side of intermediate steps) for the canvas grader, parameterized with {a}, {b}, {k}."
                        }
                    },
                    "final_answer_formula": {
                        "type": "STRING",
                        "description": "Algebraic expression for the final answer in terms of parameters, e.g. {k}, {a} - {b}, 2*{a}, etc."
                    }
                },
                "required": ["template_id", "indeterminate_form", "steps", "checkpoints", "final_answer_formula"]
            }
        }
    },
    "required": ["templates"]
}

MASTER_LIMIT_SYSTEM_PROMPT = """You are the Chief Official Examiner for the Grade 12 Cambodian National Bac II Mathematics Examination (អត្រាកំណែផ្លូវការក្រសួងអប់រំ).
Your task is to produce the OFFICIAL step-by-step mathematical blueprints for Grade 12 Bac II limit templates.

STRICT EDITORIAL AND MATHEMATICAL RULES:
1. ABSOLUTELY ZERO PROSE WORDS (STRICTLY ENFORCED):
   - ZERO English words (no "Let", "Simplify", "Evaluate", "Result", "Substitute").
   - ZERO Khmer words in the derivations (no "គេមាន", "គេបាន", "នាំឱ្យ", "ចម្លើយ").
   - The ONLY permitted text in the ENTIRE derivation is the official indeterminate form tag on line 1:
     \\left(\\text{រាងមិនកំណត់ } \\dfrac{0}{0}\\right)
     \\left(\\text{រាងមិនកំណត់ } 1^\\infty\\right)
     \\left(\\text{រាងមិនកំណត់ } \\dfrac{\\infty}{\\infty}\\right)
     \\left(\\text{រាងមិនកំណត់ } \\infty - \\infty\\right)

2. NO SKIPPED ALGEBRAIC STEPS (GRANULAR 4 TO 6 STEPS PER TEMPLATE):
   - Never take shortcuts. Show every granular algebraic transformation so high school students can follow.
   - ALWAYS maintain \\lim_{x \\to c} on every line as long as the variable x is still present.
   - Only drop \\lim on the step where the numeric target is substituted into the expression.

3. CATEGORY-SPECIFIC DERIVATION BLUEPRINTS:
   A. RATIONAL LIMITS:
      - Shifted binomials ((x+a)^n - a^n)/x:
        Line 1: State limit \\left(\\text{រាងមិនកំណត់ } \\dfrac{0}{0}\\right)
        Line 2: Expand bracket: = \\lim_{x \\to 0} \\dfrac{x^2 + 2{a}x + {a}^2 - {a}^2}{x}
        Line 3: Cancel constant: = \\lim_{x \\to 0} \\dfrac{x^2 + 2{a}x}{x}
        Line 4: Factor common x: = \\lim_{x \\to 0} \\dfrac{x(x + 2{a})}{x}
        Line 5: Cancel x: = \\lim_{x \\to 0} (x + 2{a})
        Line 6: Substitute: = 0 + 2{a} = 2{a}
      - Quadratic trinomials (x^2 + bx + c)/(x - x_0):
        Line 1: State limit with 0/0 tag
        Line 2: Factor numerator into (x - x_0)(x - x_1)
        Line 3: Cancel (x - x_0)
        Line 4: Substitute x_0 to obtain final number
      - High degree powers (x^n - a^n)/(x - a):
        Line 1: State limit with 0/0 tag
        Line 2: Split into (x - {a})(x^{n-1} + ... + {a}^{n-1})
        Line 3: Cancel (x - {a})
        Line 4: Sum of n terms equal to {a}^{n-1} -> n*{a}^{n-1}

   B. EXPONENTIAL LIMITS:
      - Second-order quadratic exponentials {k}*(e^x + e^(-x) - 2)/x^2:
        Line 1: \\lim_{x \\to 0} \\dfrac{{k}\\left(e^x + e^{-x} - 2\\right)}{x^2} \\quad \\left(\\text{រាងមិនកំណត់ } \\dfrac{0}{0}\\right)
        Line 2: Rewrite e^(-x): = \\lim_{x \\to 0} \\dfrac{{k}\\left(e^x - 2 + \\dfrac{1}{e^x}\\right)}{x^2}
        Line 3: Common denominator: = \\lim_{x \\to 0} \\dfrac{{k}\\left(e^{2x} - 2e^x + 1\\right)}{e^x \\cdot x^2}
        Line 4: Factor perfect square: = \\lim_{x \\to 0} \\dfrac{{k}\\left(e^x - 1\\right)^2}{e^x \\cdot x^2}
        Line 5: Group standard ratio: = \\lim_{x \\to 0} \\dfrac{{k}}{e^x} \\cdot \\left(\\dfrac{e^x - 1}{x}\\right)^2
        Line 6: Evaluate: = \\dfrac{{k}}{e^0} \\cdot (1)^2 = {k}
      - Difference of exponentials (e^(ax) - e^(bx))/x:
        Line 1: State limit with 0/0 tag
        Line 2: Add and subtract 1: = \\lim_{x \\to 0} \\dfrac{(e^{{a}x} - 1) - (e^{{b}x} - 1)}{x}
        Line 3: Split fractions: = \\lim_{x \\to 0} \\left(\\dfrac{e^{{a}x} - 1}{x} - \\dfrac{e^{{b}x} - 1}{x}\\right)
        Line 4: Balance coefficients: = \\lim_{x \\to 0} \\left({a} \\cdot \\dfrac{e^{{a}x} - 1}{{a}x} - {b} \\cdot \\dfrac{e^{{b}x} - 1}{{b}x}\\right)
        Line 5: Evaluate: = {a} \\cdot 1 - {b} \\cdot 1 = {a} - {b}

   C. LOGARITHMIC LIMITS:
      - Standard ratio ln(1 + ax)/(bx):
        Line 1: State limit with 0/0 tag
        Line 2: Factor constants: = \\lim_{x \\to 0} \\dfrac{{a}}{{b}} \\cdot \\dfrac{\\ln(1 + {a}x)}{{a}x}
        Line 3: Pull constant outside limit: = \\dfrac{{a}}{{b}} \\cdot \\lim_{x \\to 0} \\dfrac{\\ln(1 + {a}x)}{{a}x}
        Line 4: Evaluate standard limit: = \\dfrac{{a}}{{b}} \\cdot 1 = \\dfrac{{a}}{{b}}
      - Difference of logs (ln(x) - ln(a))/(x - a) as x -> a:
        Line 1: State limit with 0/0 tag
        Line 2: Substitute t = x - {a} with t -> 0
        Line 3: Rewrite: = \\lim_{t \\to 0} \\dfrac{\\ln(1 + t/{a})}{t}
        Line 4: Balance 1/{a}: = \\dfrac{1}{{a}} \\cdot \\lim_{t \\to 0} \\dfrac{\\ln(1 + t/{a})}{t/{a}}
        Line 5: Evaluate: = \\dfrac{1}{{a}}

   D. RADICAL LIMITS:
      - Square root conjugate (sqrt(x + c) - d)/(x - a):
        Line 1: State limit with 0/0 tag: \lim_{x \to {a}} \dfrac{\sqrt{x + {c}} - {d}}{x - {a}} \quad \left(\text{រាងមិនកំណត់ } \dfrac{0}{0}\right)
        Line 2: Multiply by conjugate: = \lim_{x \to {a}} \dfrac{(\sqrt{x + {c}} - {d})(\sqrt{x + {c}} + {d})}{(x - {a})(\sqrt{x + {c}} + {d})}
        Line 3: Expand numerator: = \lim_{x \to {a}} \dfrac{x + {c} - {d}^2}{(x - {a})(\sqrt{x + {c}} + {d})}
        Line 4: Cancel common factor: = \lim_{x \to {a}} \dfrac{1}{\sqrt{x + {c}} + {d}}
        Line 5: Substitute x = {a}: = \dfrac{1}{\sqrt{{a} + {c}} + {d}}

   E. TRIGONOMETRIC LIMITS:
      - Standard sinc ratio sin(ax)/(bx):
        Line 1: State limit with 0/0 tag: \lim_{x \to 0} \dfrac{\sin({a}x)}{{b}x} \quad \left(\text{រាងមិនកំណត់ } \dfrac{0}{0}\right)
        Line 2: Balance coefficients: = \lim_{x \to 0} \dfrac{{a}}{{b}} \cdot \dfrac{\sin({a}x)}{{a}x}
        Line 3: Pull constant outside: = \dfrac{{a}}{{b}} \cdot \lim_{x \to 0} \dfrac{\sin({a}x)}{{a}x}
        Line 4: Evaluate standard limit: = \dfrac{{a}}{{b}} \cdot 1 = \dfrac{{a}}{{b}}
      - Cosine half-angle (1 - cos(ax))/x^2:
        Line 1: State limit with 0/0 tag: \lim_{x \to 0} \dfrac{1 - \cos({a}x)}{x^2} \quad \left(\text{រាងមិនកំណត់ } \dfrac{0}{0}\right)
        Line 2: Apply half-angle formula 1 - \cos(u) = 2\sin^2(u/2): = \lim_{x \to 0} \dfrac{2\sin^2\left(\frac{{a}x}{2}\right)}{x^2}
        Line 3: Group square ratio: = \lim_{x \to 0} 2 \cdot \left(\dfrac{\sin\left(\frac{{a}x}{2}\right)}{x}\right)^2
        Line 4: Balance coefficients: = 2 \cdot \left(\dfrac{{a}}{2}\right)^2 \cdot \lim_{x \to 0} \left(\dfrac{\sin\left(\frac{{a}x}{2}\right)}{\frac{{a}x}{2}}\right)^2
        Line 5: Evaluate: = 2 \cdot \dfrac{{a}^2}{4} \cdot (1)^2 = \dfrac{{a}^2}{2}
      - Difference of sines or cosines (sum-to-product):
        Line 1: State limit with 0/0 tag
        Line 2: Apply sum-to-product trigonometric identity
        Line 3: Separate into product of sinc limits
        Line 4: Evaluate each limit factor to obtain the final value

   F. INFINITY LIMITS:
      - Rational functions P(x)/Q(x) as x -> \infty:
        Line 1: State limit with \infty/\infty tag: \lim_{x \to +\infty} \dfrac{P(x)}{Q(x)} \quad \left(\text{រាងមិនកំណត់ } \dfrac{\infty}{\infty}\right)
        Line 2: Factor out dominant power of x from numerator and denominator
        Line 3: Cancel common power of x
        Line 4: Evaluate remaining fractional terms (tending to 0) to yield the leading coefficient ratio
      - Conjugates at infinity sqrt(Ax^2 + Bx + C) - (kx + D):
        Line 1: State limit with \infty - \infty tag: \lim_{x \to +\infty} \left(\sqrt{A x^2 + B x + C} - (kx + D)\right) \quad \left(\text{រាងមិនកំណត់ } \infty - \infty\right)
        Line 2: Multiply and divide by conjugate: \dfrac{(\dots)(\dots)}{\sqrt{\dots} + (\dots)}
        Line 3: Expand numerator difference of squares
        Line 4: Factor out x from numerator and denominator
        Line 5: Evaluate limit as x -> +\infty

4. PARAMETER PRESERVATION:
   - Retain exact parameter tokens ({a}, {b}, {k}, {c}, {d}, {m}, {n}, {p}, {q}) so the blueprint is 100% universal for any numeric variant.
"""

async def generate_blueprints_for_templates(template_list: list[dict]) -> dict:
    prompt = MASTER_LIMIT_SYSTEM_PROMPT + "\n\nTEMPLATES TO SOLVE:\n"
    for idx, t in enumerate(template_list, 1):
        prompt += f"{idx}. ID: \"{t['id']}\"\n   Pattern: \"{t['pattern']}\" as {t.get('var', 'x')} -> {t.get('point', '0')}\n\n"

    resp = await _gemini_generate(
        prompt,
        response_schema=BATCH_LIMIT_SCHEMA,
        endpoint="batch_limit_blueprints"
    )
    if isinstance(resp, str):
        return json.loads(resp)
    if hasattr(resp, "text"):
        return json.loads(resp.text)
    raise RuntimeError(f"Unexpected response from Gemini: {resp}")
