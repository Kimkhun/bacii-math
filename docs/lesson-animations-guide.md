# Complete Guide: Authoring & Rendering BAC II Lesson Animations

This document is the master engineering and pedagogical guide for creating, rendering, and deploying animated lessons and formula tutorials in the BAC II Math platform.

---

## 1. Architectural Philosophy

1. **Zero-Language Video Principle**:
   - **No text words appear on screen in the video**—only mathematical symbols, arrows, geometric transformations, and numbers.
   - All explanations are external bilingual caption cues stored in `animations.json` and rendered dynamically by the web app with KaTeX.
   - **Why this matters**:
     - A single 0.3 MB MP4 serves both Khmer and English students.
     - Switching language mid-video downloads 0 new video bytes.
     - Correcting or improving Khmer wording requires **zero re-renders**.

2. **SymPy CAS Ground Truth**:
   - Animations must never show generative or approximate math.
   - Every Manim scene calls `self.check(...)` to deterministically verify all boxed expressions against SymPy before rendering completes.

3. **Active Learning Handshake**:
   - Watching an animation must always lead directly to handwriting practice.
   - When a video finishes, a completion card offers an immediate **"Try a Similar Problem on Canvas (អនុវត្តលំហាត់ស្រដៀងនេះនៅលើក្តារខៀន)"** action.

4. **Bandwidth Optimization**:
   - Pinned Manim Docker pipeline renders two versions:
     * Standard 720p H.264 (`<lesson>.mp4`) ~0.4 MB
     * Data-saver 480p H.264 (`<lesson>.480.mp4`) ~0.2 MB
     * Poster WebP (`<lesson>.webp`) ~10 KB

---

## 2. Directory Layout

| Path | Purpose |
|---|---|
| `animations/Dockerfile` | Pinned Manim 0.21.0 + SymPy 1.14.0 + ffmpeg |
| `animations/render.sh` | Shell wrapper executing `animations/render.py` inside Docker |
| `animations/render.py` | CLI renderer, encoder, webp generator, timing writer |
| `animations/verify.py` | Automated CI sweep checking media files, timings, and SymPy limits |
| `animations/common/captioned.py` | Base `CaptionedScene` recording timeline cue markers |
| `animations/common/limit_kit.py` | Reusable building blocks for limits (holes, approaching arrows, columns) |
| `animations/common/formula_kit.py` | Building blocks for formulas (curved pointers, sliding matrices, cancellations) |
| `animations/<topic>/<lesson_id>.py` | Individual Manim scenes per lesson |
| `backend/engine/topics/<topic>/data/animations.json` | Cues, start/end timestamps, and explorer IDs |
| `backend/engine/data/formula_animations.json` | Cues for formula tutorials on `/formulas` |
| `web/public/animations/<topic>/` | Output video assets (`.mp4`, `.480.mp4`, `.webp`) |
| `web/src/components/lesson/LessonVideo.tsx` | Player with Auto-pause, speed control, and Canvas bridge |
| `web/src/components/explorers/` | Interactive graph explorer components |

---

## 3. Step-by-Step: Adding a New Lesson Animation

### Step 1: Draft the Captions in `animations.json`
Add an entry in `backend/engine/topics/<topic>/data/animations.json` (or `backend/engine/data/formula_animations.json`):

```json
{
  "my_technique_id": {
    "video": "topic/my_technique_id",
    "explorer": "my_explorer_preset",
    "cues": [
      {
        "id": "intro",
        "text_en": "Identify the indeterminate form $0/0$.",
        "text_km": "ពិនិត្យទម្រង់មិនកំណត់ $0/0$។",
        "start": 0.0,
        "end": 5.0
      },
      {
        "id": "step1",
        "text_en": "Factor out $(x - 2)$ from the numerator.",
        "text_km": "ដាក់ $(x - 2)$ ជាកត្តារួមនៅភាគយក។",
        "start": 5.0,
        "end": 12.0
      }
    ]
  }
}
```

> [!NOTE]
> Initial `start` and `end` timings in the JSON can be approximate. When you render the scene in Step 3, `render.py` automatically measures exact animation cue durations and overwrites the JSON with precise timestamps.

---

### Step 2: Write the Manim Scene
Create `animations/<topic>/<lesson_id>.py`:

```python
from manim import *
import sympy as sp
from animations.common.captioned import CaptionedScene
from animations.common.style import PALETTE

class Lesson(CaptionedScene):
    lesson_id = "my_technique_id"

    def construct(self):
        # 1. SymPy Ground Truth verification
        x = sp.Symbol('x')
        self.check(sp.limit((x**2 - 4)/(x - 2), x, 2), 4)

        # 2. Cue 1: Intro
        self.cue("intro")
        title = MathTex(r"\lim_{x \to 2} \frac{x^2 - 4}{x - 2}", color=PALETTE["text"])
        self.play(Write(title))
        self.wait(1.5)

        # 3. Cue 2: Step 1
        self.cue("step1")
        factored = MathTex(r"= \lim_{x \to 2} \frac{(x-2)(x+2)}{x - 2}", color=PALETTE["text"])
        self.play(TransformMatchingTex(title, factored))
        self.wait(2.0)
```

---

### Step 3: Fast Preview (Draft Mode)
Render a quick low-resolution 480p15 preview to inspect movements without waiting for full transcode:

```bash
# Inside WSL or Linux terminal:
bash animations/render.sh limit factoring_0_0 --draft
```
Preview outputs are saved to `animations/.preview/` and touch no production files.

---

### Step 4: Production Render
When the visual timing looks smooth, run the production render:

```bash
bash animations/render.sh <topic> <lesson_id>
```

This command automatically:
1. Runs inside the pinned Docker container (`bacii-manim:0.21.0`).
2. Renders 720p H.264 animation.
3. Encodes a 480p data-saver stream.
4. Generates a WebP poster frame.
5. Computes cue timings and updates `animations.json` with duration and cache-busting version hash.
6. Writes outputs directly to `web/public/animations/<topic>/`.

---

### Step 5: Verification Sweep
Always verify that media files, SymPy checks, and cue timings match with zero gaps:

```bash
python animations/verify.py
```

---

## 4. Authentic Cambodian BAC II Terminology Standards

To keep educational explanations authentic and respectful to Grade 12 students and teachers, adhere to standard Cambodian textbook math terminology:

| English Literal | ❌ Awkward / Broken AI | ✅ Authentic BAC II Khmer |
|---|---|---|
| Brackets / Parentheses | តង្កៀប | **វង់ក្រចក** / **កន្សោម** |
| Expand brackets | ពន្លាតដូចតង្កៀបធម្មតា | **គុណពន្លាតកន្សោមតាមធម្មតា** |
| Collect terms | ប្រមូលតួនៅជាមួយគ្នា | **ផ្ដុំតួចូលគ្នា** (ផ្ដុំផ្នែកពិត និងផ្នែកនិមិត្ត) |
| Real part / numbers | ចំនួនពិតនៅជាមួយគ្នា | **ផ្នែកពិត** ($a$) |
| Imaginary part | តួដែលមាន $i$ | **ផ្នែកនិមិត្ត** ($b$) |
| Complex conjugate | ចំនួនផ្ចាស់ | **កុំផ្លិចឆ្លាស់** ($\bar{z}$) |
| Radical conjugate | ចំនួនផ្ចាស់ | **កន្សោមឆ្លាស់** |
| Cross product | ផលគុណវិចទ័រ | **ផលគុណនៃពីរវិចទ័រ** (ផលគុណខ្វែង) |
| Dot product | ផលគុណចំណុច | **ផលគុណស្កាលែ** |
| Table of values | តារាងតម្លៃលេខ | **តារាងតម្លៃ** |
| Indeterminate form | ទម្រង់មិនកំណត់ | **រាងមិនកំណត់** ($0/0, \infty/\infty$) |

---

## 5. UI Player Features Built into BAC II

1. **Auto-Pause Mode (Default ON)**:
   - Videos automatically pause at the end of each mathematical cue (`cue.end`).
   - Preference is remembered across sessions via `localStorage` (`bacii_video_autopause`).
2. **Step Controller**:
   - `Next Step ▶` (ជំហានបន្ទាប់)
   - `↺ Replay Step` (មើលជំហាននេះឡើងវិញ)
   - `◀ Prev Step` (ជំហានមុន)
3. **Speed Selector**:
   - Quick toggles for `0.75x`, `1.0x`, and `1.25x`.
4. **Canvas Bridge**:
   - Direct button triggering practice for that specific technique on canvas.
