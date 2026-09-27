import glob
import json
import os
from engine.topics.limit.structures import all_limit_structures

curated_dir = os.path.join(os.path.dirname(__file__), "..", "engine", "topics", "limit", "data", "curated")
files = sorted(glob.glob(os.path.join(curated_dir, "*.json")))

all_curated = []
for f in files:
    try:
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        formula = data.get("formula_name")
        for ex in data.get("exercises", []):
            all_curated.append({
                "file": os.path.basename(f),
                "formula": formula,
                "id": ex.get("id"),
                "prompt": ex.get("prompt_latex", "")
            })
    except Exception as e:
        print(f"Error reading {f}: {e}")

structs = all_limit_structures()
print(f"Total curated exercises in JSON: {len(all_curated)}")
print(f"Total templates in LIMIT_STRUCTURES: {len(structs)}")

matched = []
unmatched = []

for c in all_curated:
    cid = c["id"]
    # Check if id is in source_labels of any structure
    matching_structs = [s for s in structs if cid in s.get("source_labels", []) or any(cid in lbl for lbl in s.get("source_labels", []))]
    if matching_structs:
        matched.append((c, matching_structs[0]["id"]))
    else:
        unmatched.append(c)

print(f"\nExact matched by source label: {len(matched)} / {len(all_curated)}")
print(f"Items to check pattern coverage: {len(unmatched)}")

print("\n--- UNMATCHED CURATED ITEMS DETAIL ---")
for u in unmatched:
    print(f"File: {u['file']} | ID: {u['id']} | Formula: {u['formula']}")
    print(f"  Prompt: {u['prompt']}")
