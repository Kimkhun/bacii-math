"""Consistency sweep for lesson animations (run after editing or rendering).

    python3 animations/verify.py            # needs sympy (host or render image)

Checks, for every topic with a ``data/animations.json`` (and for the formula
tutorials in ``backend/engine/data/formula_animations.json``):
  * every animated lesson exists in ``lessons.json`` (every formula tutorial in
    some topic's ``formulas.json``);
  * every cue has non-empty ``text_en`` and ``text_km``, and rendered timings
    run 0 -> duration without gaps or overlaps;
  * the rendered media (720p, 480p, poster) exist under web/public/animations;
  * the explorer id is registered in the web (limitPresetIds.ts).

And for the limit explorers: the closed-form limit each preset *displays*
(web/src/components/explorers/limitPresets.ts) is mirrored below and checked
against ``sympy.limit`` at the default parameters and two others — so a slider
can never show a limit SymPy disagrees with. Keep ``LIMIT_EXPLORERS`` in step
with the presets when editing either.
"""
import json
import re
import sys
from pathlib import Path

import sympy as sp

REPO = Path(__file__).resolve().parents[1]
x = sp.Symbol("x", real=True)
oo = sp.oo

# id: (expression in x and params, point, side, closed form shown, parameter samples)
LIMIT_EXPLORERS = {
    "direct_substitution": ("x**2 + b*x + c", "a", "+-", "a**2 + b*a + c",
                            [dict(a=2, b=3, c=-1), dict(a=-1.5, b=-4, c=5), dict(a=0.5, b=1, c=0)]),
    "factoring_0_0": ("(x**2 - a**2)/(x - a)", "a", "+-", "2*a", [dict(a=3), dict(a=-2.5), dict(a=1)]),
    "rationalization_conjugate_finite": ("(sqrt(x) - sqrt(a))/(x - a)", "a", "+-", "1/(2*sqrt(a))",
                                         [dict(a=4), dict(a=1), dict(a=7)]),
    "trig_identity_0_0": ("(1 - sin(x))/cos(x)**2", "pi/2", "+-", "1/2", [{}]),
    "sinc_standard_limit": ("sin(k*x)/x", "0", "+-", "k", [dict(k=1), dict(k=sp.Rational(5, 2)), dict(k=6)]),
    "angle_addition_0_0": ("(a*sin(x) + b*cos(x))/(x - x0)", "x0", "+-", "R*cos(x0 + atan2(b, a))",
                           [dict(a=1, b=-sp.sqrt(3)), dict(a=2, b=1), dict(a=-1, b=-2)]),
    "rationalization_sinc_combo": ("(sqrt(1 + x) - sqrt(1 - x))/sin(k*x)", "0", "+-", "1/k",
                                   [dict(k=2), dict(k=sp.Rational(1, 2)), dict(k=3)]),
    "exponential_sinc_combo": ("(exp(x) + exp(-x))*sin(k*x)**2/(2*x**2)", "0", "+-", "k**2",
                               [dict(k=3), dict(k=1), dict(k=sp.Rational(7, 2))]),
    "half_angle_sinc_combo": ("(1 - cos(m*x))/x**2", "0", "+-", "m**2/2", [dict(m=4), dict(m=1), dict(m=5)]),
    "exponential_standard_limit": ("(exp(a*x) - 1)/(exp(b*x) - 1)", "0", "+-", "a/b",
                                   [dict(a=3, b=5), dict(a=-4, b=sp.Rational(1, 2)), dict(a=0, b=2)]),
    "conjugate_infinity": ("sqrt(x**2 + b*x) - x", "oo", None, "b/2", [dict(b=4), dict(b=-3), dict(b=8)]),
    "log_limit_infinity": ("x*(log(x + c) - log(x))", "oo", None, "c", [dict(c=2), dict(c=sp.Rational(1, 2)), dict(c=6)]),
    "rational_function_infinity": ("(p*x**n + 5*x)/(q*x**m + 7)", "oo", None,
                                   "Piecewise((0, n < m), (oo, n > m), ((p + 5*KroneckerDelta(n, 1))/q, True))",
                                   [dict(n=2, m=2, p=3, q=2), dict(n=1, m=1, p=3, q=2), dict(n=1, m=3, p=2, q=1),
                                    dict(n=3, m=2, p=1, q=5)]),
    "log_limit_zero": ("x**p*log(x)", "0", "+", "0", [dict(p=1), dict(p=sp.Rational(1, 10)), dict(p=2)]),
    "indeterminate_one_infinity": ("(1 + k/x)**x", "oo", None, "exp(k)", [dict(k=3), dict(k=-3), dict(k=sp.Rational(1, 2))]),
}


def angle_root(a, b):
    """Mirror of limitPresets.ts rootOf: the zero of a sin x + b cos x in [0, pi)."""
    x0 = -sp.atan2(b, a)
    while x0 < 0:
        x0 += sp.pi
    while x0 >= sp.pi:
        x0 -= sp.pi
    return sp.nsimplify(x0)


def check_explorers(errors: list[str]) -> int:
    n = 0
    for pid, (expr, point, side, shown, samples) in LIMIT_EXPLORERS.items():
        for params in samples:
            env = {k: sp.nsimplify(v) for k, v in params.items()}
            if pid == "angle_addition_0_0":
                env["x0"] = angle_root(env["a"], env["b"])
                env["R"] = sp.sqrt(env["a"] ** 2 + env["b"] ** 2)
            f = sp.sympify(expr, locals={"x": x, **{k: sp.Symbol(k) for k in env}}).subs(env)
            at = oo if point == "oo" else sp.sympify(point, locals={k: sp.Symbol(k) for k in env}).subs(env)
            got = sp.limit(f, x, at) if side is None else sp.limit(f, x, at, dir=side)
            want = sp.sympify(shown, locals={k: sp.Symbol(k) for k in env}).subs(env)
            n += 1
            if sp.simplify(got - want) != 0 and not (got == want):
                errors.append(f"explorer {pid} {params}: SymPy {got} != shown {want}")
    return n


def check_registry(errors: list[str]) -> int:
    ids_src = (REPO / "web/src/components/explorers/limitPresetIds.ts").read_text(encoding="utf-8")
    registered = set(re.findall(r'"([a-z0-9_]+)"', ids_src))
    presets_src = (REPO / "web/src/components/explorers/limitPresets.ts").read_text(encoding="utf-8")
    preset_ids = set(re.findall(r"^  ([a-z0-9_]+): \{", presets_src, flags=re.M))
    if registered != preset_ids:
        errors.append(f"limitPresetIds.ts and limitPresets.ts differ: {sorted(registered ^ preset_ids)}")
    missing = set(LIMIT_EXPLORERS) ^ preset_ids
    if missing:
        errors.append(f"verify.py LIMIT_EXPLORERS out of step with limitPresets.ts: {sorted(missing)}")

    n = 0
    for anim_path in sorted(REPO.glob("backend/engine/topics/*/data/animations.json")):
        topic = anim_path.parts[-3]
        lessons = json.loads((anim_path.parent / "lessons.json").read_text(encoding="utf-8"))
        for lid, anim in json.loads(anim_path.read_text(encoding="utf-8")).items():
            n += 1
            where = f"{topic}/{lid}"
            if lid not in lessons:
                errors.append(f"{where}: no such lesson in lessons.json")
            if anim.get("explorer") and anim["explorer"] not in registered:
                errors.append(f"{where}: explorer {anim['explorer']!r} not registered on the web")
            check_media_and_cues(where, anim, errors)

    formula_path = REPO / "backend/engine/data/formula_animations.json"
    if formula_path.exists():
        known = {tag for f in REPO.glob("backend/engine/topics/*/data/formulas.json")
                 for tag in json.loads(f.read_text(encoding="utf-8"))}
        for fid, anim in json.loads(formula_path.read_text(encoding="utf-8")).items():
            n += 1
            where = f"formulas/{fid}"
            if fid not in known:
                errors.append(f"{where}: no such formula in any topic's formulas.json")
            check_media_and_cues(where, anim, errors)
    return n


def check_media_and_cues(where: str, anim: dict, errors: list[str]) -> None:
    """Bilingual captions, cue timings that tile the video, and all three media files."""
    prev_end = 0.0
    for cue in anim["cues"]:
        if not cue.get("text_en", "").strip() or not cue.get("text_km", "").strip():
            errors.append(f"{where}/{cue['id']}: missing caption text")
        if "start" not in cue:
            errors.append(f"{where}/{cue['id']}: not rendered yet (no timing)")
            continue
        if abs(cue["start"] - prev_end) > 0.011 or cue["end"] <= cue["start"]:
            errors.append(f"{where}/{cue['id']}: bad timing {cue['start']}..{cue['end']}")
        prev_end = cue["end"]
    if "duration" in anim and abs(prev_end - anim["duration"]) > 0.011:
        errors.append(f"{where}: cues end at {prev_end}, video lasts {anim['duration']}")
    media = REPO / "web/public/animations" / anim["video"]
    for suffix in (".mp4", ".480.mp4", ".webp"):
        if not media.with_name(media.name + suffix).exists():
            errors.append(f"{where}: missing {media.name + suffix}")


def main() -> None:
    errors: list[str] = []
    lessons = check_registry(errors)
    limits = check_explorers(errors)
    for e in errors:
        print("FAIL", e)
    print(f"{lessons} animated lessons/formulas, {limits} explorer limits checked against SymPy: "
          f"{'OK' if not errors else f'{len(errors)} problem(s)'}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
