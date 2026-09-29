"""Generate per-template solution blueprints with Gemini, gated by SymPy.

For every template of a topic, Gemini writes a blueprint (definitions +
checkpoint relations + its own worked values — see
``engine/core/blueprints.py``). Each one is validated on random instances
of its template; a rejected blueprint is sent back to Gemini once more with
the exact reason SymPy rejected it. Only accepted blueprints are written to
``engine/topics/<topic>/data/blueprints.json``; the rest keep grading on
their final answer alone.

The topic plugs in through ``engine/topics/<topic>/blueprint_spec.py``
(``PROMPT``, ``RESPONSE_SCHEMA``, ``template_brief``, ``validate``,
``structures``).

Run:  cd backend && PYTHONPATH=. python scripts/generate_blueprints.py --topic derivatives
      [--only <template_id> ...] [--force] [--batch 5] [--retries 2]
      [--alternatives]    # add alternative methods (0-2 per template) to the
                          # templates that only have their standard method
      [--validate-only]   # re-check the saved file without calling Gemini

Calls Vertex AI directly (credentials from GOOGLE_APPLICATION_CREDENTIALS /
backend/credentials), so it doesn't need Redis/Postgres running; token usage
is printed rather than logged to ApiUsageLog.
"""
import argparse
import asyncio
import importlib
import json
import sys
import time

from google.genai import types

from core.config import settings
from engine.core import blueprints
from engine.llm import _gemini_client

_BLUEPRINT_KEYS = ("definitions", "compose", "checkpoints")


async def _ask(spec, briefs, feedback, model, prompt_head=None, schema=None):
    prompt = (prompt_head or spec.PROMPT) + "\n".join(json.dumps(b, ensure_ascii=False) for b in briefs)
    if feedback:
        prompt += "\n\nYOUR PREVIOUS BLUEPRINTS FOR THESE TEMPLATES WERE REJECTED BY THE CHECKER:\n"
        prompt += "\n".join(f"- {tid}: {why}" for tid, why in feedback.items())
        prompt += "\nFix exactly these problems."
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema or spec.RESPONSE_SCHEMA,
        temperature=0.2,
    )
    for wait in (10, 30, 60, None):
        try:
            resp = await asyncio.wait_for(
                _gemini_client().aio.models.generate_content(model=model, contents=prompt, config=config),
                timeout=max(settings.gemini_timeout_seconds, 120),
            )
            break
        except Exception as e:  # noqa: BLE001
            if wait is None or "429" not in str(e):
                raise
            print(f"  rate limited; retrying in {wait}s", flush=True)
            await asyncio.sleep(wait)
    usage = getattr(resp, "usage_metadata", None)
    tokens = (getattr(usage, "prompt_token_count", 0) or 0, getattr(usage, "candidates_token_count", 0) or 0)
    return json.loads(resp.text).get("templates", []), tokens


def _check(spec, struct, bp):
    try:
        return spec.validate(bp, struct)
    except Exception as e:  # noqa: BLE001 - a crash while validating is a rejection
        return [f"{type(e).__name__}: {e}"]


async def _generate(spec, targets, args, saved):
    model = args.model or settings.gemini_model
    pending = {s["id"]: s for s in targets}
    feedback: dict[str, str] = {}
    rejected: dict[str, str] = {}
    totals = [0, 0]
    for attempt in range(1 + args.retries):
        if not pending:
            break
        ids = list(pending)
        print(f"\n== attempt {attempt + 1}: {len(ids)} template(s) ==", flush=True)
        for i in range(0, len(ids), args.batch):
            chunk = ids[i:i + args.batch]
            try:
                answers, tokens = await _ask(spec, [spec.template_brief(pending[t]) for t in chunk],
                                             {t: feedback[t] for t in chunk if t in feedback}, model)
            except Exception as e:  # noqa: BLE001
                print(f"  batch {chunk}: Gemini error {type(e).__name__}: {e}", flush=True)
                continue
            totals[0] += tokens[0]
            totals[1] += tokens[1]
            by_id = {a.get("template_id"): a for a in answers}
            for tid in chunk:
                answer = by_id.get(tid)
                if answer is None:
                    feedback[tid] = "no blueprint returned for this template_id"
                    continue
                bp = {k: answer.get(k) for k in _BLUEPRINT_KEYS}
                problems = _check(spec, pending[tid], bp)
                if problems:
                    feedback[tid] = "; ".join(problems)[:600]
                    print(f"  [rejected] {tid}: {feedback[tid][:160]}", flush=True)
                    continue
                standard = {"method_id": "primary", "name_en": "Standard method", **bp,
                            "model": model, "generated_at": time.strftime("%Y-%m-%d")}
                saved[tid] = {"methods": [standard, *saved.get(tid, {"methods": []})["methods"][1:]]}
                del pending[tid]
                feedback.pop(tid, None)
                print(f"  [ok] {tid}: {len(bp['checkpoints'])} checkpoint(s)", flush=True)
            blueprints.save(args.topic, saved)
    for tid in pending:
        rejected[tid] = feedback.get(tid, "no answer")
    print(f"\ntokens: {totals[0]} prompt + {totals[1]} output ({model})")
    return rejected


def _check_alternative(spec, struct, alt, accepted):
    problems = _check(spec, struct, alt)
    if problems:
        return problems
    if not alt.get("checkpoints"):
        return ["an alternative method needs at least one checkpoint"]
    for other in accepted:
        try:
            if blueprints.same_plan(other, alt, struct, spec.instantiate):
                return [f"asks for the same intermediate results as method {other.get('method_id')!r}"]
        except Exception as e:  # noqa: BLE001
            return [f"{type(e).__name__}: {e}"]
    return []


async def _generate_alternatives(spec, targets, args, saved):
    """Add up to 2 alternative methods to templates that have a standard one."""
    model = args.model or settings.gemini_model
    pending = {s["id"]: s for s in targets}
    feedback: dict[str, str] = {}
    totals = [0, 0]
    added = 0
    for attempt in range(1 + args.retries):
        if not pending:
            break
        ids = list(pending)
        print(f"\n== attempt {attempt + 1}: {len(ids)} template(s) ==", flush=True)
        for i in range(0, len(ids), args.batch):
            chunk = ids[i:i + args.batch]
            briefs = [spec.alternative_brief(pending[t], saved[t]["methods"][0]) for t in chunk]
            try:
                answers, tokens = await _ask(spec, briefs, {t: feedback[t] for t in chunk if t in feedback},
                                             model, spec.ALTERNATIVES_PROMPT, spec.ALTERNATIVES_SCHEMA)
            except Exception as e:  # noqa: BLE001
                print(f"  batch {chunk}: Gemini error {type(e).__name__}: {e}", flush=True)
                continue
            totals[0] += tokens[0]
            totals[1] += tokens[1]
            by_id = {a.get("template_id"): a for a in answers}
            for tid in chunk:
                answer = by_id.get(tid)
                if answer is None:
                    feedback[tid] = "no entry returned for this template_id"
                    continue
                accepted = list(saved[tid]["methods"][:1])
                reasons = []
                for alt in (answer.get("methods") or [])[:2]:
                    bp = {k: alt.get(k) for k in ("method_id", "name_en", "name_km", *_BLUEPRINT_KEYS)}
                    if bp["method_id"] in {m.get("method_id") for m in accepted}:
                        bp["method_id"] = f"{bp['method_id']}_{len(accepted)}"
                    problems = _check_alternative(spec, pending[tid], bp, accepted)
                    if problems:
                        reasons.append(f"{alt.get('method_id')}: {'; '.join(problems)}"[:300])
                        continue
                    accepted.append({**bp, "model": model, "generated_at": time.strftime("%Y-%m-%d")})
                new = accepted[1:]
                if new or not reasons:
                    saved[tid] = {"methods": accepted, "alternatives_checked": time.strftime("%Y-%m-%d")}
                    added += len(new)
                    del pending[tid]
                    feedback.pop(tid, None)
                    names = ", ".join(m["method_id"] for m in new) or "none (no genuinely different method)"
                    print(f"  [ok] {tid}: {names}", flush=True)
                else:
                    feedback[tid] = " | ".join(reasons)
                    print(f"  [rejected] {tid}: {feedback[tid][:160]}", flush=True)
            blueprints.save(args.topic, saved)
    print(f"\ntokens: {totals[0]} prompt + {totals[1]} output ({model})")
    return added, {t: feedback.get(t, "no answer") for t in pending}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--force", action="store_true", help="regenerate templates that already have a blueprint")
    ap.add_argument("--batch", type=int, default=5)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--model", default=None)
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--alternatives", action="store_true",
                    help="add alternative methods to templates that have a standard one")
    args = ap.parse_args()

    spec = importlib.import_module(f"engine.topics.{args.topic}.blueprint_spec")
    structs = {s["id"]: s for s in spec.structures()}
    unknown = [t for t in args.only if t not in structs]
    if unknown:
        sys.exit(f"unknown template id(s): {unknown}")
    saved = dict(blueprints.load(args.topic, force=True))

    if args.validate_only:
        bad = {}
        n_methods = 0
        for tid, entry in saved.items():
            if tid not in structs:
                bad[tid] = "no such template (stale blueprint)"
                continue
            accepted = []
            for bp in entry["methods"]:
                n_methods += 1
                check = _check_alternative if accepted else _check
                problems = check(spec, structs[tid], bp, accepted) if accepted else check(spec, structs[tid], bp)
                if problems:
                    bad[f"{tid} [{bp.get('method_id')}]"] = "; ".join(problems)
                accepted.append(bp)
        print(f"{len(saved)} templates, {n_methods} methods: {n_methods - len(bad)} valid; "
              f"{len(structs) - len(saved)} of {len(structs)} templates have none")
        for tid, why in bad.items():
            print(f"  INVALID {tid}: {why[:200]}")
        sys.exit(1 if bad else 0)

    if args.alternatives:
        targets = [structs[t] for t in (args.only or structs) if t in saved
                   and (args.force or args.only or "alternatives_checked" not in saved[t])]
        print(f"{args.topic}: looking for alternative methods for {len(targets)} template(s)")
        added, rejected = asyncio.run(_generate_alternatives(spec, targets, args, saved))
        print(f"added {added} alternative method(s)")
        for tid, why in rejected.items():
            print(f"  NOT ACCEPTED {tid}: {why[:200]}")
        return

    targets = [structs[t] for t in (args.only or structs)
               if args.force or args.only or t not in saved]
    print(f"{args.topic}: {len(structs)} templates, {len(saved)} already have blueprints, "
          f"generating {len(targets)}")
    rejected = asyncio.run(_generate(spec, targets, args, saved))
    print(f"accepted {len(targets) - len(rejected)}/{len(targets)}; "
          f"{len(saved)}/{len(structs)} templates now have a blueprint")
    for tid, why in rejected.items():
        print(f"  NOT ACCEPTED {tid}: {why[:200]}")


if __name__ == "__main__":
    main()
