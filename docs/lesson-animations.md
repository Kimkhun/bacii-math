# Lesson animations: Watch (Manim) + Explore (interactive)

An animated lesson gets two buttons in `LessonModal`, under the summary:

- **Watch animation** plays a 3Blue1Brown-style video rendered offline with
  [Manim](https://www.manim.community/).
- **Explore** opens an interactive widget. Students drag across a graph or move
  sliders to experiment with the concept.

Pilot scope: all 15 **limit** lessons. Other topics use the same pattern.

## Pieces

| Where | What |
|---|---|
| `animations/` | Manim scenes and the render pipeline (Python, runs in Docker) |
| `animations/common/captioned.py` | `CaptionedScene`: splits the timeline into caption cues and records their timings |
| `animations/common/limit_kit.py` | Limit building blocks: graph with a hole, points approaching from both sides, zoom, algebra column. Also the two shared storyboards (`hole_story`, `infinity_story`) and `check()` |
| `animations/<topic>/<lesson_id>.py` | One `Lesson` scene per lesson |
| `animations/render.sh` | Renders, encodes and registers videos inside the pinned image (`animations/Dockerfile`) |
| `animations/verify.py` | Consistency sweep (see Verification) |
| `backend/engine/topics/<topic>/data/animations.json` | Per lesson: `video`, `explorer`, the bilingual `cues`, plus `start`/`end`/`duration`/`version` written by the render |
| `backend/engine/core/lesson_animations.py` | Merges `animations.json` into the `GET /lessons` payload as `animation` |
| `web/public/animations/<topic>/` | `<lesson>.mp4` (720p), `<lesson>.480.mp4` (data saver), `<lesson>.webp` (poster) |
| `web/src/components/lesson/` | `LessonAnimationPanel` (the two buttons) and `LessonVideo` (player, synced captions, step buttons, HD/data-saver switch) |
| `web/src/components/explorers/` | `LimitExplorer` (generic), `limitPresets.ts` (one preset per lesson), `UnitCirclePanel`, the registry in `index.tsx` |

## Design rules

- **Videos carry no language.** Only math appears on screen. Every word a student
  reads is a cue caption in `animations.json`, rendered by the web under the
  player with KaTeX. This has three effects:
  - one video serves Khmer and English;
  - switching language mid-video downloads nothing;
  - fixing a caption's wording needs no re-render (only its timing comes from
    the render).
- **SymPy is still the source of truth.**
  - Every scene calls `check()` with the limit it boxes. The render fails if
    SymPy disagrees.
  - Scenes take their prompt and answer from the lesson's own example.
  - Explorers evaluate floats in the browser **only to draw**. The limit they
    display is the closed form from the lesson's formula sheet (drawn as the
    exact hole), and `verify.py` re-checks those closed forms with SymPy.
- **Bandwidth.**
  - Encoding: H.264 720p, `-tune animation`, CRF 28, faststart, no audio. The
    pilot averages **0.45 MB/min**, so a lesson video is 0.2–0.5 MB. The budget
    warns above 1.5 MB/min and fails above 3.
  - The 480p data-saver file is chosen automatically when the connection reports
    `saveData` or 2g/3g. The student's own choice is remembered.
  - `preload="none"` means no video bytes move until play; only the ~10 KB poster
    loads when Watch is pressed.
  - Media is served `Cache-Control: immutable` (`web/next.config.mjs`). The web
    appends `?v=<version>` (a content hash), so a re-render changes the URL.
- **No server cost, no idle client cost.**
  - Explorers are lazily-loaded chunks of about 17 KB.
  - They re-render only on input and never run an animation loop.
  - The SVG is sized to its real pixel width, so labels stay legible on phones.

## Adding or changing an animated lesson

1. **Captions.** Add an entry in `<topic>/data/animations.json`: `video`, `explorer`,
   and `cues` (`id`, `text_en`, `text_km`). Each cue is held on screen at least
   as long as its longer language takes to read (`reading_time`).
2. **Scene.** Write `animations/<topic>/<lesson_id>.py` with a `Lesson` scene:
   - Set `lesson_id`, call `self.check(...)`, then `self.cue("<id>")` before
     each part.
   - The cue ids must match `animations.json` exactly, in order.
   - For limits, `hole_story` (0/0 at a point) or `infinity_story` (x → +∞)
     usually does it in about 20 lines.
3. **Preview.** `animations/render.sh <topic> <lesson_id> --draft` writes a fast
   480p15 preview to `animations/.preview/` and touches nothing else.
4. **Render.** `animations/render.sh <topic> [<lesson_id> …]` writes the media
   files plus the timings, `duration` and `version`, and prints a size table.
5. **Explorer.**
   - Add a preset to `limitPresets.ts` and its id to `limitPresetIds.ts`.
   - Mirror its closed form in `verify.py` `LIMIT_EXPLORERS`.
   - For a new topic, add its own explorer component and register it in
     `explorers/index.tsx`.
6. **Verify.** Run `python3 animations/verify.py`.

For a new topic, also call `with_animation(...)` in that topic's `lessons.py`
`get_lesson` (see `engine/topics/limit/lessons.py`).

## Verification

`python3 animations/verify.py` (needs SymPy) checks:

- every animated lesson exists;
- every cue has both languages and the timings tile the video with no gaps;
- all three media files exist;
- the explorer id is registered on the web;
- every explorer's displayed limit equals `sympy.limit` at the default and
  other parameter values.

## Hosting

The pilot's media is about 7 MB, committed directly to git. Git LFS isn't
worth the deploy step at this size.

When the library grows, move `web/public/animations` to object storage behind
a CDN (e.g. a GCS bucket, since we already use GCP for Vertex AI) and set
`NEXT_PUBLIC_ANIMATION_BASE_URL`. No code changes are needed.

With `output: "standalone"`, a production image must copy `public/` next to
the server. The dev compose bind-mounts it.

## Known limits / next steps

- The pilot covers limits only. The other topics (complex plane, conics,
  vectors, …) need their own kits and explorers.
- On a phone held upright, the math in the videos is small; fullscreen or
  landscape is comfortable. If students find it hard to read, scale up
  `LimitScene.problem` / `column` / the axis numbers.
- Khmer captions were drafted alongside the English and should get a native
  speaker's review.
- The Flutter app (`mobile/`) does not show animations yet. The data is in the
  same `/lessons` payload, so a player there only needs `video_player` and the
  same base URL.
