import asyncio
import json
import os
import sys

from engine.topics.limit.structures import all_limit_structures
from scripts.experiment_gemini_limits import generate_blueprints_for_templates

BLUEPRINT_PATH = "/app/data/limit_blueprints.json"

def get_target_templates():
    targets = []
    for s in all_limit_structures():
        targets.append({
            "id": s["id"],
            "pattern": s["pattern"],
            "point": s.get("point", "0"),
            "var": s.get("var", "x")
        })
    return targets

async def main():
    targets = get_target_templates()
    total_all = len(targets)
    print(f"Total target templates across all families: {total_all}", flush=True)

    existing_blueprints = {}
    if os.path.exists(BLUEPRINT_PATH):
        try:
            with open(BLUEPRINT_PATH, encoding="utf-8") as f:
                existing_blueprints = json.load(f)
        except Exception:
            existing_blueprints = {}

    to_generate = [t for t in targets if t["id"] not in existing_blueprints]
    print(f"Templates already cached: {len(existing_blueprints)} / {total_all}", flush=True)
    print(f"Templates to generate now: {len(to_generate)} / {total_all}", flush=True)

    # Process in chunks of 2 with brief pause for rate limits
    batch_size = 2
    for i in range(0, len(to_generate), batch_size):
        chunk = to_generate[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(to_generate) + batch_size - 1) // batch_size
        print(f"\n--- Batch {batch_num}/{total_batches} ({len(chunk)} items) ---", flush=True)
        for t in chunk:
            print(f" * {t['id']}: {t['pattern']}", flush=True)

        # Retry loop for transient 429 / network errors
        for attempt in range(2):
            try:
                res = await generate_blueprints_for_templates(chunk)
                for bp in res.get("templates", []):
                    tid = bp["template_id"]
                    existing_blueprints[tid] = bp
                    print(f" [OK] {len(existing_blueprints)}/{total_all} - {tid} ({len(bp.get('steps', []))} steps)", flush=True)
                break
            except Exception as e:
                print(f" Attempt {attempt+1} failed: {repr(e)}", flush=True)
                if attempt == 0:
                    print(" Waiting 8s before retry...", flush=True)
                    await asyncio.sleep(8)

        # Save progress atomically
        tmp_path = BLUEPRINT_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(existing_blueprints, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, BLUEPRINT_PATH)

        # Small delay between batches to stay under rate limits
        await asyncio.sleep(1.2)

    print(f"\n=== FINISHED ===\nTotal blueprints saved in {BLUEPRINT_PATH}: {len(existing_blueprints)}/{total_all}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
