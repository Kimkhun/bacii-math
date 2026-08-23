# Canvas internals (`web/src/components/Canvas.tsx`)

Everything about the handwriting canvas: the strokes model, the layered
rendering, the "infinite paper" growth, zoom/pan/pinch, the export/overlay
coordinate systems, and the backend box pipeline it pairs with.

## Public surface (the imperative handle)

`CanvasHandle` (exposed via `useImperativeHandle`) is the contract the practice
page uses:

| Method | Purpose |
|---|---|
| `getImageBase64()` | The exported image for OCR (white background + ink) — or the original uploaded image when one was loaded. Returns `null` when there's no ink. |
| `getExportMap()` | Maps exported-image pixel coords → canvas internal coords (see Coordinate spaces). |
| `getLineSnapshots(boxes)` | Per-line ink region copies (small images) for the line-pop animation. `null`s for a loaded image (no ink layer). |
| `hasInk()` / `canUndo()` | Ink present / something to undo (strokes or a loaded image). |
| `loadImage(dataUrl)` | Set an uploaded photo as the page content (strokes are cleared). |
| `clear()` | Reset ink, image, and canvas size to initial; scroll to top. |
| `setTool / setPenWidth / setEraserWidth` | Tool & width refs (pen `3/6/10`, eraser default `32`). |
| `undo()` | Pop the last stroke (or remove a loaded image) and repaint. |

Props: `fullscreen`, `width/height`, `zoom`, `onZoomChange`, `onChange` (ink
changed), `overlay` (SVG layer rendered above the ink — used for the red-pen
marks, line pops, and review-mode writing).

## Coordinate spaces (get this right first)

1. **Internal space** — `W × H` (the canvas bitmap). Starts `1600 × 1000`
   (`FULL_W/FULL_H`), grows up to `12000 × 12000`. All strokes, boxes, and
   overlays live here.
2. **Display space** — the canvas element is CSS-scaled to `W·zoom × H·zoom`
   inside a scrollable wrapper; `getPos()` maps pointer `clientX/Y` → internal
   via `getBoundingClientRect`.
3. **Export space** — what OCR sees:
   - Drawn strokes → a fresh `W × H` canvas (white + ink) → **identical to
     internal space** (`getExportMap` scale 1, offset 0).
   - Loaded image → the **original image bytes** (natural size), which the page
     displays centered + scaled → `getExportMap` returns that scale/offset.
4. **Overlay space** — the overlay SVG is `W·zoom × H·zoom` CSS pixels with
   `viewBox="0 0 W H"`, so internal coords map 1:1 at any zoom. Marks are drawn
   in internal coords directly; OCR boxes (export space) are converted with
   `getExportMap()` before use.

## Strokes model

```ts
interface Stroke { points: Point[]; tool: "pen" | "eraser"; width: number }
```

- `strokesRef` holds every stroke in order (pen strokes and eraser strokes
  mixed). It is the source of truth — the bitmaps are derived.
- Rendering a stroke: `drawSmoothPath` draws quadratic curves through
  consecutive midpoints (smooth, not jagged), dot for 1-point strokes, straight
  line for 2 points. Pen ink is `#1f2937`, round caps/joins.

## Layered rendering (why it's fast)

Three canvases, composed left-to-right:

1. **Background layer** (`bgCanvasRef`) — the ruled paper (fill `#fdfdfd`,
   margin line `#f2b8b8` at x=64, ruling `#c9d7f0` every 40px). Rendered **once
   per canvas size** into its own canvas; recomposited via `drawImage` instead
   of redrawing ~300 lines every pointer move (this was the cursor-lag fix).
2. **Ink layer** (`inkCanvasRef`) — persistent, transparent canvas holding all
   drawn ink. Eraser strokes use `destination-out` directly on it, so erasing
   never touches the background. Resizing clears it; `replayStrokesToInk()`
   rebuilds it from `strokesRef` (lossless).
3. **Display canvas** (`canvasRef`) — composites bg + ink (or the loaded image).

Two repaint paths:

- `redraw()` (full) — bg + `replayStrokesToInk()` + ink. Used on start, undo,
  clear, resize, load.
- `redrawCurrentStroke()` (per-move) — bg + replay **only the in-progress
  stroke** onto the persistent ink layer (opaque pen overdraw / idempotent
  eraser erase — both safe) + ink. O(current stroke) instead of O(all
  strokes). `requestRedraw()` coalesces calls to **one repaint per animation
  frame** (rAF).

## "Infinite paper" growth

- Triggered in `start`/`move` via `maybeGrow(p)` when the pointer is within
  `GROW_THRESHOLD = 220` px of an edge and below `MAX_*`; grows `GROW_CHUNK =
  700` per event.
- `growingRef` is a reentry guard cleared after the resize effect runs.
- **Scroll compensation happens ONLY for left-growth** (`grownRef = {top: 0,
  left: growLeft}`). Left growth physically relocates existing strokes
  (`shiftStrokesX`), so the view must follow them. Bottom/right growth keeps
  the view exactly where the user is — no auto-scroll, so the pen is never
  dragged into the new space mid-stroke (the phantom-straight-line bug).
- The resize effect redraws (full replay, needed since the ink bitmap was
  reallocated), applies the left scroll, and clears the growing guard.

## Zoom, pan, pinch

- Zoom is a **prop** (0.5–2.5, stepped in the toolbar). The canvas is CSS-scaled
  — internal coordinates never change.
- Desktop: **hold Space** → `panningRef` mode → drag scrolls the wrapper
  (delta from the pan start anchor). Wheel/zoom buttons live in the UI.
- Touch: two fingers → `pinchRef` (center + distance); move scales zoom around
  the pinch center and anchors scroll; a second finger down cancels any
  in-flight single-finger stroke first.
- A custom cursor element (`fixed`, sized by tool width × zoom, styled per
  tool) tracks the pointer and hides on leave.

## Input handling & palm rejection

- Pointer events (`onPointerDown/Move/Up/Cancel`, `pointerLeave` ends).
- While a stylus (`pointerType === "pen"`) is active, stray touch contacts are
  ignored entirely (resting palm).
- Touch pointers are tracked in a map; 2 → pinch; >2 ignored.
- Drawing is disabled when a loaded image is present (you can only view it).

## Export & OCR integration (the backend side)

1. `getImageBase64()` — for strokes: white + ink at `W × H`; for a loaded
   image: the original image.
2. Backend `engine/vision.py` preprocesses (crop-to-ink + pad 24, upscale to
   ≤1024, max ×4) and asks the OCR for per-line **normalized** boxes
   (`lines_boxes`). The upscale factor cancels in the mapping: original coords
   = crop offset + normalized · crop size. Invalid boxes are dropped
   (`_map_boxes_to_original`).
3. The web sends `lines_boxes` with the grade; the backend persists them on the
   attempt (`attempts.lines_boxes`) so **review mode** (`/practice?attempt=…`)
   can re-draw the OCR'd writing at its original positions via
   `getExportMap()` + the overlay.
4. `getLineSnapshots(boxes)` copies each line's ink region (6px pad) into small
   images for the live line-pop animation; returns all-`null` for loaded
   images (no ink layer).

## Known constraints / gotchas

- A 12000px-tall canvas bitmap is ~large; always use the cached bg + incremental
  ink paths during drawing (never full `redraw()` per move).
- After a mid-stroke grow, the resize effect full-replays — subsequent moves
  resume incremental rendering on the restored layer.
- Eraser strokes are idempotent when replayed (destination-out twice = once).
- `getPos` uses the CSS-scaled rect, so zoom is inherently handled.
- The non-fullscreen variant (question card preview) is a fixed-ratio box with
  no zoom/grow/overlay.
- The rAF callback guards against a null canvas ref (post-unmount safety).

## Related docs

- `pipeline.md` — the request flow this canvas plugs into.
- `step-checking.md` — how `step_check` verdicts become the marks drawn here.
- `adding-question-types.md` — adding new question types (formula tags → marks).