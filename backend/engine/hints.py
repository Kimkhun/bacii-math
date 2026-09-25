"""Socratic Hint Engine for BAC II Math.

Analyzes a student's active exercise, active sub-part, and currently written
or typed scratchwork (via SymPy line-by-line verification). Generates an
expert Cambodian high school math teacher guiding clue:
- Names the relevant formula or identity.
- Diagnoses whether the student is stuck at start, made an algebra error,
  or used an unfruitful formula.
- Guides them toward the next action without spoiling the final answer.
- Defaults to 100% authentic Khmer.
"""
from __future__ import annotations

import logging
from typing import Any

from . import grader, llm, solver
from .concurrency import run_in_thread
from .notation import pretty_expr

log = logging.getLogger(__name__)


def _extract_part_context(question_spec: dict, solution: dict, part_label: str | None) -> dict:
    """Extract prompt, expected answer, and steps for the active sub-part."""
    parts = solution.get("parts") or []
    if not parts or not part_label:
        return {
            "part_label": None,
            "prompt": question_spec.get("prompt") or "",
            "expected": str(solution.get("answer_exact", "")),
            "formula_tags": solution.get("formula_tags", []),
            "steps": solution.get("steps", []),
        }

    # Find matching part by label (e.g. "A", "B", "1", "2")
    part_obj = next((p for p in parts if str(p.get("label")) == str(part_label)), None)
    if not part_obj:
        part_obj = parts[0]

    return {
        "part_label": part_obj.get("label"),
        "prompt": part_obj.get("question_km") or part_obj.get("question_en") or "",
        "expected": str(part_obj.get("answer_exact", "")),
        "formula_tags": part_obj.get("technique") or solution.get("formula_tags", []),
        "technique": part_obj.get("technique_km") or part_obj.get("technique") or "",
        "steps": [part_obj] if "steps" not in part_obj else part_obj["steps"],
    }


def _diagnose_work(
    topic: str,
    question_type: str,
    spec: dict,
    work_lines: list[str],
) -> dict:
    """Run SymPy line-by-line verification to find the student's exact blocker."""
    cleaned = [ln.strip() for ln in work_lines if ln.strip()]
    if not cleaned:
        return {"status": "blank", "lines": []}

    try:
        analysis = grader.analyze_work(topic, question_type, spec, cleaned)
    except Exception as e:
        log.warning("analyze_work failed in hint diagnosis: %s", e)
        return {"status": "unverified", "lines": cleaned}

    first_err = analysis.get("first_error_line")
    line_results = analysis.get("line_results", [])
    completed_steps = [r for r in line_results if r.get("matches")]

    if first_err:
        err_line_text = cleaned[first_err - 1] if 0 < first_err <= len(cleaned) else ""
        return {
            "status": "calculation_error",
            "error_line_number": first_err,
            "error_line_text": err_line_text,
            "completed_steps": len(completed_steps),
            "lines": cleaned,
        }

    if completed_steps:
        return {
            "status": "in_progress",
            "completed_steps": len(completed_steps),
            "last_correct_line": cleaned[-1],
            "lines": cleaned,
        }

    return {
        "status": "unrecognized",
        "lines": cleaned,
    }


def _build_hint_prompt(
    question_prompt: str,
    part_ctx: dict,
    diagnosis: dict,
    solution: dict,
    lang: str = "km",
) -> str:
    status = diagnosis.get("status")
    part_label = part_ctx.get("part_label")
    part_str = f"ផ្នែក {part_label}" if part_label else "លំហាត់នេះ"

    if lang == "km":
        prompt_parts = [
            "អ្នកគឺជាលោកគ្រូ/អ្នកគ្រូបង្រៀនគណិតវិទ្យាថ្នាក់ទី១២ ថ្នាក់ជាតិ (បាក់ឌុប) ដ៏ជំនាញ និងរួសរាយ។",
            "សិស្សកំពុងអនុវត្តលំហាត់ ហើយបានចុចប៊ូតុង 'សុំជំនួយ (Hint)'។",
            f"ប្រធានលំហាត់៖ {question_prompt}",
        ]
        if part_label:
            prompt_parts.append(f"សំណួរដែលកំពុងធ្វើ ({part_str})៖ {part_ctx.get('prompt')}")

        if status == "blank":
            prompt_parts.append(
                "ស្ថានភាពសិស្ស៖ សិស្សទើបតែចាប់ផ្តើម ហើយមិនទាន់បានសរសេរអ្វីនៅលើក្ដារខៀននៅឡើយទេ។\n"
                "គោលបំណងជំនួយ៖ ប្រាប់សិស្សអំពី រូបមន្ត ឬជំហានទី១ ដែលត្រូវយកមកប្រើដើម្បីចាប់ផ្តើមដោះស្រាយ ដោយមិនប្រាប់ចម្លើយចុងក្រោយឡើយ។"
            )
        elif status == "calculation_error":
            err_num = diagnosis.get("error_line_number")
            err_text = diagnosis.get("error_line_text")
            prompt_parts.append(
                f"ស្ថានភាពសិស្ស៖ សិស្សបានសរសេរ scratchwork មួយចំនួន ប៉ុន្តែមានកំហុសគណនា ឬសញ្ញានៅបន្ទាត់ទី {err_num} គឺ៖ '{err_text}'។\n"
                "គោលបំណងជំនួយ៖ ចង្អុលបង្ហាញកំហុសត្រង់បន្ទាត់នោះដោយទន់ភ្លន់ (ឧ. ច្រឡំសញ្ញា, ភ្លេចស្វ័យគុណ ឬអនុវត្តរូបមន្តមិនទាន់ត្រូវ) "
                "ហើយប្រាប់រូបមន្តត្រឹមត្រូវដើម្បីកែតម្រូវ និងបន្តទៅមុខទៀត។"
            )
        elif status == "in_progress":
            last_line = diagnosis.get("last_correct_line")
            prompt_parts.append(
                f"ស្ថានភាពសិស្ស៖ សិស្សបានគណនាត្រឹមត្រូវរហូតមកដល់បន្ទាត់៖ '{last_line}'។\n"
                "គោលបំណងជំនួយ៖ សរសើរការគិតត្រឹមត្រូវរបស់ពួកគេមួយម៉ាត់ រួចផ្តល់ជំនួយអំពី រូបមន្ត ឬជំហានបន្ទាប់ដែលត្រូវធ្វើបន្ត "
                "(ឧទាហរណ៍៖ ត្រូវសម្រួលកត្តាណា ឬអនុវត្តលីមីតគំរូ/អាំងតេក្រាលណា) ដោយមិនបញ្ចេញចម្លើយស្រេចនោះទេ។"
            )
        else:
            prompt_parts.append(
                f"ស្ថានភាពសិស្ស៖ សិស្សបានសរសេរ៖ {diagnosis.get('lines')} ប៉ុន្តែមិនទាន់ត្រូវទម្រង់ដោះស្រាយ។\n"
                "គោលបំណងជំនួយ៖ ណែនាំរូបមន្តគន្លឹះ និងទិសដៅដោះស្រាយត្រឹមត្រូវសម្រាប់ដំណាក់កាលនេះ។"
            )

        prompt_parts.extend([
            "\nលក្ខខណ្ឌតឹងរ៉ឹង៖",
            "១. ត្រូវឆ្លើយជាភាសាខ្មែរ ១០០% តាមរចនាបថគ្រូបង្រៀនកម្ពុជា។",
            "២. ហាមប្រាប់ចម្លើយចុងក្រោយដាច់ខាត (DO NOT reveal the final answer value)។",
            "៣. ផ្តោតសំខាន់លើ រូបមន្តគណិតវិទ្យា (Formula) និងសកម្មភាពគណនាបន្ទាប់។",
            "៤. រាល់កន្សោមគណិតវិទ្យា ត្រូវសរសេរក្នុងទម្រង់ LaTeX ដោយព័ទ្ធជុំវិញដោយ $...$ (ឧ. $\\sin^2 x + \\cos^2 x = 1$)។",
            "៥. សរសេរខ្លីល្មម ត្រឹមតែ ២ ទៅ ៤ បន្ទាត់ ដើម្បីងាយស្រួលអានលើទូរស័ព្ទ ឬថេប្លេត។ គ្មានពាក្យស្វាគមន៍វែងឆ្ងាយឡើយ។",
        ])
        return "\n".join(prompt_parts)

    # English fallback
    prompt_parts = [
        "You are an encouraging Grade 12 math teacher helping a student who clicked 'Hint'.",
        f"QUESTION: {question_prompt}",
    ]
    if part_label:
        prompt_parts.append(f"CURRENT SUB-PART ({part_label}): {part_ctx.get('prompt')}")

    if status == "blank":
        prompt_parts.append(
            "STUDENT STATE: The student hasn't written anything yet.\n"
            "GOAL: Give them a guiding hint on which initial formula or rule to use to start, without giving away the answer."
        )
    elif status == "calculation_error":
        prompt_parts.append(
            f"STUDENT STATE: Calculation error on line {diagnosis.get('error_line_number')}: '{diagnosis.get('error_line_text')}'.\n"
            "GOAL: Point out the issue gently (e.g. sign error, missed term) and guide them on what formula will fix it."
        )
    elif status == "in_progress":
        prompt_parts.append(
            f"STUDENT STATE: Student did well up to line: '{diagnosis.get('last_correct_line')}'.\n"
            "GOAL: Acknowledge their correct work and guide them toward the NEXT formula or operation to perform."
        )
    else:
        prompt_parts.append(
            f"STUDENT STATE: Written work: {diagnosis.get('lines')}.\n"
            "GOAL: Guide them toward the correct formula for this step."
        )

    prompt_parts.extend([
        "\nSTRICT RULES:",
        "- DO NOT reveal the final answer value.",
        "- Focus on the mathematical formula and the next immediate step.",
        "- Wrap all math expressions in $...$.",
        "- Keep it concise: 2 to 4 sentences maximum.",
    ])
    return "\n".join(prompt_parts)


async def generate_hint(
    topic: str,
    question_type: str,
    spec: dict,
    question_prompt: str,
    part: str | None = None,
    work_text: str | None = None,
    lang: str = "km",
    user_id: Any = None,
) -> dict:
    """Generate a contextual teacher hint based on student's current work."""
    try:
        solution = await run_in_thread(solver.solve, topic, question_type, spec)
    except Exception as e:
        log.warning("solve failed in generate_hint: %s", e)
        solution = {}

    part_ctx = _extract_part_context(spec, solution, part)
    work_lines = [ln.strip() for ln in (work_text or "").split("\n") if ln.strip()]
    diagnosis = await run_in_thread(_diagnose_work, topic, question_type, spec, work_lines)

    prompt = _build_hint_prompt(
        question_prompt=question_prompt,
        part_ctx=part_ctx,
        diagnosis=diagnosis,
        solution=solution,
        lang=lang,
    )

    hint_text, provider = await llm._generate_with_fallback(
        prompt, allow_gemini=True, endpoint="hint", user_id=user_id
    )

    if not hint_text:
        # Fallback if AI call fails
        if lang == "km":
            technique = part_ctx.get("technique") or "សូមពិនិត្យមើលរូបមន្តគ្រឹះនៃលំហាត់នេះ"
            hint_text = f"💡 ជំនួយ៖ {technique}។ សូមព្យាយាមអនុវត្តជំហានដំបូងនៃរូបមន្តនេះ។"
        else:
            hint_text = "💡 Hint: Check the core formula for this topic and apply the first algebraic step."
        provider = "fallback"

    return {
        "hint": hint_text,
        "provider": provider,
        "part": part,
        "status": diagnosis.get("status"),
        "error_line": diagnosis.get("error_line_number"),
    }
