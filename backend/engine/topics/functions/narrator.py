"""Dedicated Khmer reference solution generator for Bac II function studies.
Enforces authentic MoEYS Grade 12 national exam editorial standards and
strictly prohibits verbose AI word salad.
"""
import json
from google.genai import types


async def narrate_function_part(part_fact: dict, gemini_generate_fn, part_tool_decl, user_id: any = None) -> dict | None:
    """Generate a crisp, authentic MoEYS reference solution for one part of a function study."""
    authored = (part_fact.get("authored_technique") or "").strip()
    want = part_fact.get("want", "")
    label = part_fact.get("label", "")
    q_km = part_fact.get("question_km", "")

    prompt = (
        "You are the chief official examiner for the Cambodian National Bac II Mathematics Examination (អត្រាកំណែផ្លូវការក្រសួងអប់រំ) for Grade 12.\n"
        f"Question Label: {label}\n"
        f"Question (Khmer): {q_km}\n"
        f"Part Want: {want}\n"
        f"SymPy-verified Steps & Data:\n{json.dumps(part_fact, ensure_ascii=False)}\n\n"
    )

    if authored:
        prompt += (
            f"AUTHORITATIVE TEACHER'S SOLUTION (អត្រាកំណែគំរូផ្លូវការ):\n{authored}\n\n"
            "INSTRUCTION FOR AUTHORITATIVE SOLUTION:\n"
            "- Follow the exact mathematical derivation, concise phrasing, and equations in the teacher's solution above.\n"
            "- Break it into a clean list of `steps` (state condition/formula -> show algebraic steps -> conclusion).\n"
            "- Keep the crisp concluding line in `answer_khmer` (e.g. ដូចនេះ ...).\n\n"
        )

    prompt += (
        "STRICT BAC II EDITORIAL RULES:\n"
        "1. PROHIBITED WORD SALAD (ABSOLUTELY FORBIDDEN):\n"
        "   - Do NOT write conversational filler or unneeded narrative introductions.\n"
        "   - NEVER write phrases like: 'គណនាលីមីតនៃអនុគមន៍ f កាលណា...', 'តាមរយៈផលចែក និងសំណល់នៃការចែកពហុធា គេបាន...', 'ដោយធ្វើការចែកពហុធាភាគយកនិងភាគបែង...', 'ដោយប្រៀបធៀបកន្សោម... ជាមួយទម្រង់... គេទាញបាន...'\n"
        "   - Do NOT repeat the question statement inside the steps.\n"
        "2. REQUIRED STRUCTURE & CONNECTORS:\n"
        "   - The `khmer` field of EACH step must contain the full step line with its mathematical formulas embedded inside $...$ (e.g. `យើងមាន $f(x) = x + \\frac{1}{x-2}$` or `ព្រោះ $\\lim_{x \\to 2^-} f(x) = -\\infty$ និង $\\lim_{x \\to 2^+} f(x) = +\\infty$`). NEVER put raw Khmer words into the `latex` field.\n"
        "   - The `latex` field should contain only the isolated pure math equation without Khmer words.\n"
        "   - Start directly with the formula or given expression: គេមាន $...$ ឬ យើងមាន $...$\n"
        "   - Use standard MoEYS connectors: យើងបាន, ព្រោះ, និង, ហើយ, ដោយ..., នាំឱ្យ, ដូចនេះ.\n"
        "   - Wrap ALL mathematical equations and numbers in $...$.\n"
        "3. QUESTION-SPECIFIC GUIDELINES:\n"
        "   - For Domain of definition (ដែនកំណត់): state the condition (e.g. អនុគមន៍មានន័យលុះត្រាតែ $... \\neq 0$), deduce the restriction, and conclude with standard minus sign: $D = \\mathbb{R} - \\{a\\}$ or $D = \\mathbb{R} - \\{a, b\\}$. ABSOLUTELY NEVER use `\\setminus` (it renders as an awkward backslash in KaTeX).\n"
        "   - If finding limits and vertical asymptote: show one-sided limits and infinity limits directly, then conclude: ដោយ $\\lim_{x \\to a} f(x) = \\pm\\infty$ នោះបន្ទាត់សមីការ $x = a$ ជាអាស៊ីមតូតឈរនៃ $(C)$ ។\n"
        "   - If decomposition and oblique asymptote: write decomposition $f(x) = ... = x + \\frac{1}{x-2} \\quad (1)$, compare with form $(2)$ to state $\\alpha, \\beta, \\gamma$, and show $\\lim_{x \\to \\pm\\infty} [f(x) - y] = 0$ to deduce $(d) : y = ax+b$ is the oblique asymptote.\n"
        "   - If derivative and variation: show $f'(x) = ...$, state the sign rule, state roots $x_1, x_2$, and calculate local extrema ($f(x_1), f(x_2)$). Do NOT output array tables (\\begin{array}) because the UI renders the graphical variation table automatically.\n"
        "   - If tangent line: recall the formula $(T): y = f'(x_0)(x - x_0) + f(x_0)$, evaluate $f'(x_0)$ and $f(x_0)$, and conclude the equation of $(T)$.\n"
        "   - If center or axis of symmetry: translate coordinates $\\begin{cases} x = X + x_0 \\\\ y = Y + y_0 \\end{cases}$, show $Y = F(X)$ satisfies $F(-X) = -F(X)$ (អនុគមន៍សេស) or $F(-X) = F(X)$ (អនុគមន៍គូ), and conclude $I(x_0, y_0)$ is the center of symmetry or $x = x_0$ is the axis of symmetry.\n"
        "   - If relative position: consider $f(x) - y$, analyze the sign on each interval, and conclude where $(C)$ is above or below the line.\n"
        "4. You MUST call the `submit_part_solution` tool with the filled `steps`, `answer_khmer`, and `answer_latex`."
    )

    try:
        tool = types.Tool(function_declarations=[part_tool_decl])
        resp = await gemini_generate_fn(prompt, tools=[tool], endpoint="km_solution_function", user_id=user_id)
        if hasattr(resp, "function_calls") and resp.function_calls:
            for call in resp.function_calls:
                if call.name == "submit_part_solution":
                    args = call.args
                    if isinstance(args, dict) and "steps" in args:
                        return args
        if hasattr(resp, "text") and resp.text:
            text = resp.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            if isinstance(data, dict) and "steps" in data:
                return data
        return None
    except Exception:
        return None
