"""Render, encode and register lesson animations. Run through ``render.sh``.

For each animated lesson of a topic (the keys of its ``animations.json``):

1. render ``animations/<topic>/<lesson>.py``'s ``Lesson`` scene with Manim at
   720p30 (``--draft``: 480p15 into ``animations/.preview/``, nothing else touched);
2. encode it for the web, tuned for students on mobile data —
   ``<lesson>.mp4`` (720p H.264, ``-tune animation``, faststart, no audio),
   ``<lesson>.480.mp4`` (data-saver variant) and ``<lesson>.webp`` (poster);
3. merge the scene's cue timings back into ``animations.json``
   (``start``/``end`` per cue, ``duration``, and ``version`` = content hash used
   by the web to cache-bust), after checking the scene used exactly the
   authored cue ids, in order;
4. enforce the size budget (MB per minute of 720p video).
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg

REPO = Path(__file__).resolve().parents[1]
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
BUDGET_WARN_MB_PER_MIN = 1.5
BUDGET_FAIL_MB_PER_MIN = 3.0


def animations_path(topic: str) -> Path:
    if topic == "formulas":  # formula tutorials: one registry keyed by formula id
        return REPO / "backend" / "engine" / "data" / "formula_animations.json"
    return REPO / "backend" / "engine" / "topics" / topic / "data" / "animations.json"


def ffmpeg(*args: str) -> None:
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def render_scene(topic: str, lesson_id: str, workdir: Path, draft: bool) -> tuple[Path, dict]:
    cues_out = workdir / "cues.json"
    env = {
        **os.environ,
        "CUES_OUT": str(cues_out),
        "BACII_REPO": str(REPO),
        "PYTHONPATH": str(REPO / "animations"),
    }
    scene = REPO / "animations" / topic / f"{lesson_id}.py"
    subprocess.run(
        ["manim", "render", "-ql" if draft else "-qm", "--disable_caching", "--progress_bar", "none", "-v", "WARNING",
         "--media_dir", str(workdir), "-o", "raw", str(scene), "Lesson"],
        check=True, env=env,
    )
    raw = next(workdir.rglob("raw.mp4"))
    return raw, json.loads(cues_out.read_text(encoding="utf-8"))


def merge_cues(anim: dict, timing: dict, lesson_id: str) -> None:
    authored = [c["id"] for c in anim["cues"]]
    used = [c["id"] for c in timing["cues"]]
    if authored != used:
        raise SystemExit(f"{lesson_id}: scene cues {used} != authored cues {authored}")
    starts = [c["start"] for c in timing["cues"]]
    ends = starts[1:] + [timing["duration"]]
    for cue, start, end in zip(anim["cues"], starts, ends):
        cue["start"], cue["end"] = round(start, 2), round(end, 2)
    anim["duration"] = round(timing["duration"], 2)


def poster_time(anim: dict) -> float:
    """A frame that shows the setup without giving the answer away: just
    before the cue named by ``poster_cue`` (default: the last cue) begins."""
    target = anim.get("poster_cue") or anim["cues"][-1]["id"]
    cue = next(c for c in anim["cues"] if c["id"] == target)
    return max(0.0, cue["start"] - 0.2)


def encode(raw: Path, out_dir: Path, lesson_id: str, anim: dict) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    hd, sd, poster = (out_dir / f"{lesson_id}.mp4", out_dir / f"{lesson_id}.480.mp4",
                      out_dir / f"{lesson_id}.webp")
    common = ["-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-pix_fmt", "yuv420p",
              "-movflags", "+faststart", "-an"]
    ffmpeg("-i", str(raw), *common, "-crf", "28", str(hd))
    ffmpeg("-i", str(raw), "-vf", "scale=-2:480", *common, "-crf", "30", str(sd))
    ffmpeg("-ss", f"{poster_time(anim):.2f}", "-i", str(raw), "-frames:v", "1", "-vf", "scale=960:-2",
           "-c:v", "libwebp", "-quality", "72", str(poster))
    return {"hd": hd, "sd": sd, "poster": poster}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("topic")
    ap.add_argument("lessons", nargs="*", help="lesson ids (default: every animated lesson)")
    ap.add_argument("--draft", action="store_true", help="fast 480p15 preview into animations/.preview/")
    args = ap.parse_args()

    path = animations_path(args.topic)
    registry = json.loads(path.read_text(encoding="utf-8"))
    lesson_ids = args.lessons or list(registry)
    unknown = [lid for lid in lesson_ids if lid not in registry]
    if unknown:
        raise SystemExit(f"not in {path.relative_to(REPO)}: {unknown}")

    rows, failed = [], []
    for lesson_id in lesson_ids:
        anim = registry[lesson_id]
        with tempfile.TemporaryDirectory() as tmp:
            raw, timing = render_scene(args.topic, lesson_id, Path(tmp), args.draft)
            merge_cues(anim, timing, lesson_id)
            if args.draft:
                preview = REPO / "animations" / ".preview" / args.topic
                preview.mkdir(parents=True, exist_ok=True)
                shutil.copy(raw, preview / f"{lesson_id}.mp4")
                print(f"preview: {(preview / f'{lesson_id}.mp4').relative_to(REPO)}")
                continue
            out = encode(raw, REPO / "web" / "public" / "animations" / args.topic, lesson_id, anim)
        anim["version"] = hashlib.sha256(out["hd"].read_bytes()).hexdigest()[:10]
        mb = {k: p.stat().st_size / 1e6 for k, p in out.items()}
        per_min = mb["hd"] / (anim["duration"] / 60)
        flag = "FAIL" if per_min > BUDGET_FAIL_MB_PER_MIN else "warn" if per_min > BUDGET_WARN_MB_PER_MIN else "ok"
        if flag == "FAIL":
            failed.append(lesson_id)
        rows.append((lesson_id, anim["duration"], mb["hd"], mb["sd"], mb["poster"] * 1000, per_min, flag))

    if args.draft:
        return
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n{'lesson':34} {'secs':>6} {'720p MB':>8} {'480p MB':>8} {'poster KB':>9} {'MB/min':>7}")
    for lid, secs, hd, sd, kb, per_min, flag in rows:
        print(f"{lid:34} {secs:6.1f} {hd:8.2f} {sd:8.2f} {kb:9.0f} {per_min:7.2f}  {flag}")
    total = sum(r[2] + r[3] + r[4] / 1000 for r in rows)
    print(f"total media written: {total:.1f} MB")
    if failed:
        sys.exit(f"over the {BUDGET_FAIL_MB_PER_MIN} MB/min budget: {failed}")


if __name__ == "__main__":
    main()
