"""Import blueprints written outside the Gemini loop (by hand, or by another
model) through exactly the same SymPy gate as ``generate_blueprints.py``.

The input file has the shape the generator's LLM returns:

  standard methods:  {"templates": [{"template_id", "definitions", "compose", "checkpoints"}, ...]}
  --alternatives:    {"templates": [{"template_id", "methods": [{"method_id", "name_en",
                                     "name_km", "definitions", "compose", "checkpoints"}]}]}

Each blueprint is validated (``spec.validate``; alternatives also must differ
from the methods already accepted, ``same_plan``) and only accepted ones are
saved, recording `--model` as the author. A rejected one prints SymPy's
reason and changes nothing.

Run:  cd backend && PYTHONPATH=. python scripts/import_blueprints.py --topic <topic> --file plans.json
      --model <who wrote them> [--alternatives] [--force]
"""
import argparse
import importlib
import json
import sys
import time

from engine.core import blueprints
from scripts.generate_blueprints import _BLUEPRINT_KEYS, _check, _check_alternative


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--model", required=True, help="who wrote these blueprints (recorded per method)")
    ap.add_argument("--alternatives", action="store_true")
    ap.add_argument("--force", action="store_true", help="replace a template's existing standard method")
    args = ap.parse_args()

    spec = importlib.import_module(f"engine.topics.{args.topic}.blueprint_spec")
    structs = {s["id"]: s for s in spec.structures()}
    saved = dict(blueprints.load(args.topic, force=True))
    with open(args.file, encoding="utf-8") as f:
        entries = json.load(f)["templates"]
    today = time.strftime("%Y-%m-%d")
    accepted, rejected = 0, 0
    for entry in entries:
        tid = entry.get("template_id")
        if tid not in structs:
            print(f"  [unknown] {tid}")
            rejected += 1
            continue
        if args.alternatives:
            if tid not in saved:
                print(f"  [rejected] {tid}: no standard method to add alternatives to")
                rejected += 1
                continue
            methods = list(saved[tid]["methods"][:1])
            for alt in entry.get("methods") or []:
                bp = {k: alt.get(k) for k in ("method_id", "name_en", "name_km", *_BLUEPRINT_KEYS)}
                problems = _check_alternative(spec, structs[tid], bp, methods)
                if problems:
                    print(f"  [rejected] {tid} [{bp['method_id']}]: {'; '.join(problems)[:300]}")
                    rejected += 1
                    continue
                methods.append({**bp, "model": args.model, "generated_at": today})
                accepted += 1
                print(f"  [ok] {tid} [{bp['method_id']}]")
            saved[tid] = {"methods": methods, "alternatives_checked": today}
            if not entry.get("methods"):
                print(f"  [ok] {tid}: no genuinely different method")
        else:
            if tid in saved and not args.force:
                print(f"  [skip] {tid}: already has a blueprint (--force to replace)")
                continue
            bp = {k: entry.get(k) for k in _BLUEPRINT_KEYS}
            problems = _check(spec, structs[tid], bp)
            if problems:
                print(f"  [rejected] {tid}: {'; '.join(problems)[:300]}")
                rejected += 1
                continue
            standard = {"method_id": "primary", "name_en": "Standard method", **bp,
                        "model": args.model, "generated_at": today}
            saved[tid] = {"methods": [standard, *saved.get(tid, {"methods": []})["methods"][1:]]}
            accepted += 1
            print(f"  [ok] {tid}: {len(bp['checkpoints'])} checkpoint(s)")
    blueprints.save(args.topic, saved)
    print(f"accepted {accepted}, rejected {rejected}; {len(saved)}/{len(structs)} templates have a blueprint")
    sys.exit(1 if rejected else 0)


if __name__ == "__main__":
    main()
