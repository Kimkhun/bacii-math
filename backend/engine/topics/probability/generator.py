"""Probability generation: sample a user-owned scenario, fill the Khmer/English
frames, and hand the filled params to the solver (the math authority)."""
from ...core.expr_shared import _build_expr_problem
from . import scenarios


def _generate_probability(rng, difficulty, question_type=None, variant=None):
    """Pick a multi-part exercise from the user-owned catalog, sample valid
    params, fill the Khmer (or English) sentences — setup on its own line, then
    every sub-part A/B/C/D on its own line — and return the problem. The solver
    computes every part's answer afterwards; the catalog only owns the story and
    the param *possibility* constraints."""
    if question_type not in (None, "probability"):
        raise ValueError(f"question_type {question_type} does not match topic probability")
    if difficulty not in scenarios.VARIANT_BY_DIFFICULTY:
        raise ValueError(f"unknown difficulty: {difficulty}")

    pool = [variant] if variant and variant in scenarios.SCENARIOS else None
    if pool is None:
        pool = list(scenarios.VARIANT_BY_DIFFICULTY.get(difficulty, ()))
        if not pool:
            pool = list(scenarios.SCENARIOS)
    if not pool:
        raise ValueError(f"no probability scenarios for difficulty {difficulty}")
    rng.shuffle(pool)

    for sid in pool:
        entry = scenarios.by_id(sid)
        envs = scenarios.sample_scenario(entry, rng)
        if not envs:
            continue

        lines = []
        setup = entry.get("setup_km") or entry.get("setup_en") or ""
        if setup:
            lines.append(scenarios.fill_frame(setup, envs[0]["env"]))
        parts = entry.get("parts") or []
        part_params = []
        for i, pe in enumerate(envs):
            part = parts[i] if i < len(parts) else {}
            frame = part.get("km") or part.get("en") or pe.get("km") or ""
            if not frame:
                continue
            lines.append(scenarios.fill_frame(frame, pe["env"]))
            part_params.append({"label": pe["label"], "want": pe["want"], **pe["env"]})
        if len(part_params) < 1:
            continue
        try:
            text = "\n".join(lines)
        except ValueError:
            continue

        params = {
            "structure": entry["structure"],
            "variant": sid,
            "scenario_id": sid,
            "target": part_params[-1]["label"],
            "parts": part_params,
        }
        display = f"probability ({entry['structure']})"
        return _build_expr_problem(
            "probability", "probability", params, difficulty, text, None, display
        )
    raise ValueError(f"no scenario could produce a valid problem for difficulty {difficulty}")