"use client";

import { forwardRef, ReactNode, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState } from "react";

export type CanvasTool = "pen" | "eraser" | "ruler" | "axes" | "curve" | "ellipse" | "select";

// A spawned coordinate system on the paper (background layer, not ink): axes
// crossing at (ox, oy) with integer gridlines every stepX/stepY units (each
// unit = `scale` pixels), tick marks + numeric labels on each axis starting at
// 0. Tick extents are recomputed from the current paper size at draw time, so
// the grid auto-extends as the canvas grows. Drawn behind the ink so the
// eraser can't damage it and OCR/thumbnail exports exclude it.
export interface GridState {
  ox: number;
  oy: number;
  stepX: number;
  stepY: number;
  scale: number;
}

export interface CanvasExportMap {
  canvasW: number;
  canvasH: number;
  scale: number;
  offsetX: number;
  offsetY: number;
}

export interface CanvasHandle {
  getImageBase64: () => string | null;
  getInkSnapshot: () => string | null;
  getExportMap: () => CanvasExportMap;
  getLineSnapshots: (boxes: (number[] | null)[]) => (LineSnapshot | null)[];
  getStrokes: () => StrokeDocument | null;
  getStrokesThumb: (maxWidth?: number) => string | null;
  hasInk: () => boolean;
  loadImage: (dataUrl: string) => void;
  loadStrokes: (data: StrokeDocument) => void;
  loadBackgroundInk: (dataUrl: string) => void;
  clear: () => void;
  setTool: (tool: CanvasTool) => void;
  setPenWidth: (width: number) => void;
  setEraserWidth: (width: number) => void;
  undo: () => void;
  canUndo: () => boolean;
  redo: () => void;
  canRedo: () => boolean;
  eraseRegion: (box: number[]) => void;
  spawnGrid: (stepX: number, stepY: number, origin?: { x: number; y: number } | null, scale?: number) => void;
  setGridSteps: (stepX: number, stepY: number) => void;
  setGridScale: (scale: number) => void;
  moveGrid: (ox: number, oy: number) => void;
  hideGrid: () => void;
  fitGridToWindow: (xMin: number, xMax: number, yMin: number, yMax: number) => void;
  hasGrid: () => boolean;
}

export interface LineSnapshot {
  x: number;
  y: number;
  w: number;
  h: number;
  href: string;
}

interface Point {
  x: number;
  y: number;
  // 0..1, only meaningful when the owning stroke's pointerType is "pen" —
  // an Apple Pencil / stylus reports real pressure; mouse and touch report a
  // constant (0.5 or 1), so we only let pressure affect width for "pen".
  pressure?: number;
}

interface PathStroke {
  kind: "path";
  points: Point[];
  tool: CanvasTool;
  width: number;
  pointerType?: string;
}

// A straight segment drawn with the ruler tool (pen-down = start point, drag =
// preview, pen-up = commit). Stored as its own stroke kind so it's undoable,
// erasable, and survives save/resume like any other stroke.
interface LineStroke {
  kind: "line";
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  tool: "ruler";
  width: number;
}

// A smooth, freely-editable curve: an open path through any number of anchor
// points joined by cubic béziers. Each anchor carries an in/out control handle
// (absolute coords); when synthesized from a drag we derive smooth handles from
// the neighbours (Catmull-Rom), so a drag comes out smooth and then stays
// editable point-by-point afterwards (Photoshop/Illustrator-style). Undoable,
// erasable, serializable like any stroke.
interface Anchor {
  x: number;
  y: number;
  hIn: { x: number; y: number };
  hOut: { x: number; y: number };
}

interface CurveStroke {
  kind: "curve";
  tool: "curve";
  anchors: Anchor[];
  width: number;
}

// An axis-aligned ellipse drawn with the ellipse tool (drag corner-to-corner;
// cx/cy/rx/ry define the bounding box). Useful for conic sketches.
interface EllipseStroke {
  kind: "ellipse";
  cx: number;
  cy: number;
  rx: number;
  ry: number;
  tool: "ellipse";
  width: number;
}

// A rectangular region erase (used by "write it again" on a mis-read line) —
// modeled as its own stroke kind so it survives replayStrokesToInk() (canvas
// resizes) and participates in undo/redo like any other stroke.
interface RectStroke {
  kind: "rect";
  rect: { x1: number; y1: number; x2: number; y2: number };
}

// A previously-drawn page restored as a single flattened layer (used when
// returning to a question navigated away from mid-answer). Unlike
// loadImage()/imageRef (the "uploaded photo" path, which is read-only and
// blocks further drawing), this is just another stroke — the student can keep
// writing on top of it, erase parts of it, and undo it as one step.
interface RasterStroke {
  kind: "raster";
  img: HTMLImageElement;
  w: number;
  h: number;
}

type Stroke = PathStroke | RectStroke | RasterStroke | LineStroke | CurveStroke | EllipseStroke;

// What part of a selected shape an edit-drag is manipulating.
type EditState = { mode: "anchor" | "hIn" | "hOut" | "move" | "corner"; index: number; px: number; py: number };

// The serializable subset of a stroke document. Raster strokes are excluded —
// they hold an HTMLImageElement (from loadBackgroundInk) that can't be
// JSON-serialized, so only vector pen/eraser ink survives in history/resume.
type SerializableStroke = Exclude<Stroke, RasterStroke>;

// Deep-copy a single stroke (incl. curve anchor handles) so exports / undo
// snapshots never alias the live refs (a pointer still writing would otherwise
// mutate the saved snapshot later).
function cloneStrokeDeep(s: Stroke): Stroke {
  if (s.kind === "curve") {
    return {
      ...s,
      anchors: s.anchors.map((a) => ({ x: a.x, y: a.y, hIn: { ...a.hIn }, hOut: { ...a.hOut } })),
    };
  }
  if (s.kind === "rect") return { ...s, rect: { ...s.rect } };
  if (s.kind === "path") return { ...s, points: s.points.map((p) => ({ ...p })) };
  if (s.kind === "raster") return s;
  return { ...s };
}

// Deep-copy strokes so the exported document never aliases the live refs (a
// pointer still writing would otherwise mutate the saved snapshot later).
function cloneStrokes(arr: Stroke[]): SerializableStroke[] {
  return arr
    .filter((s): s is SerializableStroke => s.kind !== "raster")
    .map((s) => cloneStrokeDeep(s) as SerializableStroke);
}

// Serializable stroke document — the full state Canvas.getStrokes() exports and
// loadStrokes() restores. width/height capture the canvas size at save time
// (the page grows while writing), strokes is the ordered history (including
// eraser strokes), and redoStack lets a restored session keep undo/redo.
export interface StrokeDocument {
  width: number;
  height: number;
  strokes: SerializableStroke[];
  redoStack: SerializableStroke[];
  grid?: GridState | null;
}

const PAPER_COLOR = "#fdfcf8";
const LINE_COLOR = "rgba(214, 221, 232, 0.85)"; // #d6dde8 @ 85%
const MARGIN_COLOR = "rgba(230, 201, 196, 0.9)"; // #e6c9c4 @ 90%
const INK_COLOR = "#1e2a38";
const LINE_SPACING = 40;
const MARGIN_X = 64;
export const FULL_W = 1600;
export const FULL_H = 1000;
const ERASER_WIDTH = 32;

// "Infinite paper": while the user is writing near the bottom of the page, grow
// the canvas by another chunk rather than cutting them off — never grows while
// the user is just scrolling around to review earlier work.
const GROW_CHUNK = 700;
const GROW_THRESHOLD = 220;
const MAX_HEIGHT = 12000;
const MAX_WIDTH = 12000;

export const PEN_WIDTHS = { thin: 3, medium: 6, thick: 10 } as const;
const DEFAULT_PEN_WIDTH = PEN_WIDTHS.medium;

// Draws a stroke's points as a smooth curve (quadratic through consecutive
// midpoints) instead of straight jagged segments between raw pointer samples.
function drawSmoothPath(ctx: CanvasRenderingContext2D, points: Point[]) {
  if (points.length === 0) return;
  if (points.length === 1) {
    const r = ctx.lineWidth / 2;
    ctx.beginPath();
    ctx.arc(points[0].x, points[0].y, r, 0, Math.PI * 2);
    ctx.fillStyle = ctx.strokeStyle as string;
    ctx.fill();
    return;
  }
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  if (points.length === 2) {
    ctx.lineTo(points[1].x, points[1].y);
    ctx.stroke();
    return;
  }
  for (let i = 1; i < points.length - 1; i++) {
    const mid = { x: (points[i].x + points[i + 1].x) / 2, y: (points[i].y + points[i + 1].y) / 2 };
    ctx.quadraticCurveTo(points[i].x, points[i].y, mid.x, mid.y);
  }
  const last = points[points.length - 1];
  ctx.lineTo(last.x, last.y);
  ctx.stroke();
}

// 0.55x..1.25x of the selected pen size — enough to feel like a real nib
// (thin on light touch, fuller on a firm press) without letting a heavy hand
// blow a line out past what's still legible/OCR-able.
const PRESSURE_MIN_SCALE = 0.55;
const PRESSURE_MAX_SCALE = 1.25;

// Same smoothing as drawSmoothPath, but strokes each midpoint-to-midpoint
// segment individually with a width interpolated from that segment's
// pressure — a tapered, pressure-sensitive line like a real stylus app
// (Notability/GoodNotes/Procreate), instead of one uniform-width path.
function drawPressurePath(ctx: CanvasRenderingContext2D, points: Point[], baseWidth: number) {
  if (points.length === 0) return;
  const widthAt = (p: Point) => {
    const pr = p.pressure ?? 0.5;
    const scale = PRESSURE_MIN_SCALE + pr * (PRESSURE_MAX_SCALE - PRESSURE_MIN_SCALE);
    return Math.max(1, baseWidth * scale);
  };
  if (points.length === 1) {
    const r = widthAt(points[0]) / 2;
    ctx.beginPath();
    ctx.arc(points[0].x, points[0].y, r, 0, Math.PI * 2);
    ctx.fillStyle = ctx.strokeStyle as string;
    ctx.fill();
    return;
  }
  let prevMid = points[0];
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i];
    const p1 = points[i + 1];
    const mid = i === points.length - 2 ? p1 : { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 };
    ctx.lineWidth = widthAt(p0);
    ctx.beginPath();
    ctx.moveTo(prevMid.x, prevMid.y);
    ctx.quadraticCurveTo(p0.x, p0.y, mid.x, mid.y);
    ctx.stroke();
    prevMid = mid;
  }
}

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 2.5;

const Canvas = forwardRef<
  CanvasHandle,
  {
    width?: number;
    height?: number;
    fullscreen?: boolean;
    onChange?: () => void;
    zoom?: number;
    onZoomChange?: (zoom: number) => void;
    overlay?: ReactNode;
    onToolAutoSwitch?: (tool: CanvasTool) => void;
  }
>(({ width = 640, height = 820, fullscreen = false, onChange, zoom = 1, onZoomChange, overlay, onToolAutoSwitch }, ref) => {
    const initialW = fullscreen ? FULL_W : width;
    const initialH = fullscreen ? FULL_H : height;
    const [canvasWidth, setCanvasWidth] = useState(initialW);
    const [canvasHeight, setCanvasHeight] = useState(initialH);
    const W = fullscreen ? canvasWidth : width;
    const H = fullscreen ? canvasHeight : height;
    // All canvas buffers (ink, ruled background, the visible element) are
    // sized at W*dpr / H*dpr physical pixels — matching a Retina screen's real
    // pixel density — instead of just W/H. Every consumer keeps drawing in
    // plain logical W/H coordinates; a ctx.setTransform(dpr,...) right after
    // getting a context is what maps that onto the bigger physical buffer, so
    // strokes are rasterized crisply instead of being drawn low-res and then
    // upscaled/blurred to fill the screen (the actual cause of the pixelation
    // — the canvas simply had fewer physical pixels than the display needed).
    // Browser zoom changes window.devicePixelRatio; keeping dpr as reactive state
    // (refreshed on window resize) means every repaint uses the current pixel
    // ratio, so the background/grid/ink layers don't vanish or blur after zoom.
    const [dpr, setDpr] = useState<number>(() =>
      Math.min(typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1, 3)
    );
    useEffect(() => {
      const onResize = () => setDpr(Math.min(window.devicePixelRatio || 1, 3));
      window.addEventListener("resize", onResize);
      return () => window.removeEventListener("resize", onResize);
    }, []);
    useEffect(() => {
      // dpr changed → buffer sizes changed; drop the cached layers and repaint.
      bgCanvasRef.current = null;
      inkCanvasRef.current = null;
      redraw();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [dpr]);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const wrapperRef = useRef<HTMLDivElement>(null);
    // Ink lives on its own transparent layer so erasing (destination-out) never
    // touches the ruled background drawn underneath it.
    const inkCanvasRef = useRef<HTMLCanvasElement | null>(null);
    const bgCanvasRef = useRef<HTMLCanvasElement | null>(null);
    const rafRef = useRef<number | null>(null);
    const strokesRef = useRef<Stroke[]>([]);
    const redoStackRef = useRef<Stroke[]>([]);
    const imageRef = useRef<HTMLImageElement | null>(null);
    const imageDataRef = useRef<string | null>(null);
    const drawing = useRef(false);
    // Which pointer is actually drawing the in-progress stroke. `drawing` alone
    // isn't enough — it's a single shared flag, so without this a second,
    // unrelated pointer (a resting palm generating its own move/up events)
    // would pass the `drawing.current` check in move()/end() and either splice
    // its own coordinates into the real stroke or end it prematurely.
    const drawingPointerIdRef = useRef<number | null>(null);
    const toolRef = useRef<CanvasTool>("pen");
    const penWidthRef = useRef<number>(DEFAULT_PEN_WIDTH);
    const eraserWidthRef = useRef<number>(ERASER_WIDTH);
    const gridRef = useRef<GridState | null>(null);
    const cursorElRef = useRef<HTMLDivElement>(null);
    // Axes drag-to-pan: origin + pointer position at drag start.
    const gridPanRef = useRef<{ px: number; py: number; ox: number; oy: number } | null>(null);
    // Curve tool: samples during the drag to find the bend (max deviation).
    const curveSamplesRef = useRef<Point[]>([]);
    // Ellipse tool: the corner where the drag started.
    const ellipseStartRef = useRef<Point | null>(null);
    // Editable-shape selection state (Select tool / auto-select after drawing).
    const curvePathRef = useRef<Point[]>([]);
    const selectedRef = useRef<number | null>(null);
    const hoverIndexRef = useRef<number | null>(null);
    const hoverPointRef = useRef<Point | null>(null);
    const editingRef = useRef<EditState | null>(null);
    const editSnapshotRef = useRef<Stroke | null>(null);
    const lastTapRef = useRef<{ t: number; x: number; y: number }>({ t: 0, x: 0, y: 0 });
    const onToolAutoSwitchRef = useRef<((t: CanvasTool) => void) | undefined>(undefined);
    onToolAutoSwitchRef.current = onToolAutoSwitch;

    const updateCursor = (clientX: number, clientY: number) => {
      const el = cursorElRef.current;
      if (!el) return;
      // Select tool: show a real cursor that reflects move / resize / anchor
      // state instead of the pen-size ring.
      if (toolRef.current === "select") {
        el.style.display = "none";
        const cv = canvasRef.current;
        if (!cv) return;
        let cursor = "default";
        const p = getPos(clientX, clientY, undefined);
        const sel = selectedRef.current;
        if (editingRef.current) {
          const m = editingRef.current.mode;
          cursor =
            m === "move" || m === "anchor"
              ? "move"
              : m === "corner"
              ? cornerCursor(editingRef.current.index)
              : "crosshair";
        } else if (sel != null) {
          const s = strokesRef.current[sel];
          const h = hitTestHandle(s, p);
          if (h) cursor = h.mode === "corner" ? cornerCursor(h.index) : h.mode === "anchor" ? "move" : "crosshair";
          else if (shapeHit(s, p)) cursor = "move";
          else if (hitTestShape(p) != null) cursor = "move";
        } else if (hitTestShape(p) != null) {
          cursor = "move";
        }
        cv.style.cursor = cursor;
        return;
      }
      // Non-select tools: clear any leftover select-mode inline cursor.
      if (canvasRef.current) canvasRef.current.style.cursor = "";
      if (toolRef.current === "axes") {
        el.style.width = "18px";
        el.style.height = "18px";
        el.style.background = "transparent";
        el.style.border = "1.5px solid #334155";
        el.style.borderRadius = "2px";
        el.style.left = `${clientX}px`;
        el.style.top = `${clientY}px`;
        el.style.display = "block";
        return;
      }
      const isPen = toolRef.current !== "eraser";
      const w = Math.max(2, (isPen ? penWidthRef.current : eraserWidthRef.current) * zoom);
      el.style.width = `${w}px`;
      el.style.height = `${w}px`;
      el.style.left = `${clientX}px`;
      el.style.top = `${clientY}px`;
      if (isPen) {
        el.style.background = "rgba(31, 41, 55, 0.12)";
        el.style.border = "1px solid rgba(31, 41, 55, 0.7)";
      } else {
        el.style.background = "rgba(255, 255, 255, 0.4)";
        el.style.border = "1.5px solid #1f2937";
      }
      el.style.display = "block";
    };

    const hideCursor = () => {
      if (cursorElRef.current) cursorElRef.current.style.display = "none";
    };

    const getInkCanvas = () => {
      // Rounded once and compared/assigned as the same integer throughout —
      // canvas.width/height always read back as whole pixels, but W * dpr is
      // essentially never exactly one (devicePixelRatio is a float like
      // 1.7999999523162842), so comparing against the raw product mismatched
      // on nearly every call. That made getInkCanvas() clear+resize (wiping
      // whatever was just painted) on every single call instead of only on
      // real size changes — including the second call in redraw(), right
      // after replayStrokesToInk() had just repainted it, and on every
      // pointer-move frame during redrawCurrentStroke(). Net effect: ink was
      // drawn correctly but erased again before it ever reached the screen.
      const w = Math.round(W * dpr);
      const h = Math.round(H * dpr);
      if (!inkCanvasRef.current) {
        const c = document.createElement("canvas");
        c.width = w;
        c.height = h;
        inkCanvasRef.current = c;
      } else if (inkCanvasRef.current.height !== h || inkCanvasRef.current.width !== w) {
        // Resizing clears the buffer; replayStrokesToInk() (called right after,
        // everywhere this matters) repaints it from strokesRef, which is lossless.
        inkCanvasRef.current.width = w;
        inkCanvasRef.current.height = h;
      }
      return inkCanvasRef.current;
    };

    const strokeStyleFor = (ctx: CanvasRenderingContext2D, tool: CanvasTool, width: number) => {
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      if (tool === "eraser") {
        ctx.globalCompositeOperation = "destination-out";
        ctx.lineWidth = width;
      } else {
        ctx.globalCompositeOperation = "source-over";
        ctx.strokeStyle = INK_COLOR;
        ctx.lineWidth = width;
      }
    };

    const drawRuled = (ctx: CanvasRenderingContext2D) => {
      ctx.fillStyle = PAPER_COLOR;
      ctx.fillRect(0, 0, W, H);
      const grid = gridRef.current;
      if (grid) {
        // A coordinate grid replaces the ruled writing paper entirely.
        drawGrid(ctx, grid);
        return;
      }
      ctx.lineWidth = 1;
      ctx.strokeStyle = MARGIN_COLOR;
      ctx.beginPath();
      ctx.moveTo(MARGIN_X, 0);
      ctx.lineTo(MARGIN_X, H);
      ctx.stroke();
      ctx.strokeStyle = LINE_COLOR;
      for (let y = LINE_SPACING; y < H; y += LINE_SPACING) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(W, y);
        ctx.stroke();
      }
    };

    // Coordinate system spawned on the background layer: black axes through the
    // origin, faint gray gridlines at each step plus even fainter half-step
    // minor lines (line only, no label), black tick marks + numeric labels on
    // each axis starting at 0. Tick extents are computed from the CURRENT paper
    // W/H, so the grid extends automatically as the infinite canvas grows.
    const drawGrid = (ctx: CanvasRenderingContext2D, grid: GridState) => {
      const { ox, oy, stepX, stepY, scale } = grid;
      const dx = stepX * scale;
      const dy = stepY * scale;
      if (dx <= 0 || dy <= 0) return;
      const fmt = (v: number) => String(Number(v.toFixed(2)));
      const left = Math.ceil(ox / dx);
      const right = Math.ceil((W - ox) / dx);
      const up = Math.ceil(oy / dy);
      const down = Math.ceil((H - oy) / dy);
      ctx.save();
      ctx.lineWidth = 1;
      // half-step minor lines (no labels)
      ctx.strokeStyle = "rgba(15, 23, 42, 0.05)";
      for (let i = -2 * left - 1; i <= 2 * right + 1; i++) {
        const x = ox + (i / 2) * dx;
        if (i % 2 === 0) continue;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, H);
        ctx.stroke();
      }
      for (let i = -2 * down - 1; i <= 2 * up + 1; i++) {
        const y = oy - (i / 2) * dy;
        if (i % 2 === 0) continue;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(W, y);
        ctx.stroke();
      }
      // major gridlines
      ctx.strokeStyle = "rgba(15, 23, 42, 0.1)";
      for (let i = -left; i <= right; i++) {
        const x = ox + i * dx;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, H);
        ctx.stroke();
      }
      for (let i = -down; i <= up; i++) {
        const y = oy - i * dy;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(W, y);
        ctx.stroke();
      }
      // axes (black)
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "#1e293b";
      ctx.beginPath();
      ctx.moveTo(0, oy);
      ctx.lineTo(W, oy);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(ox, 0);
      ctx.lineTo(ox, H);
      ctx.stroke();
      // tick marks
      ctx.lineWidth = 1;
      ctx.strokeStyle = "#334155";
      const tick = 5;
      for (let i = -left; i <= right; i++) {
        if (i === 0) continue;
        const x = ox + i * dx;
        ctx.beginPath();
        ctx.moveTo(x, oy - tick);
        ctx.lineTo(x, oy + tick);
        ctx.stroke();
      }
      for (let i = -down; i <= up; i++) {
        if (i === 0) continue;
        const y = oy - i * dy;
        ctx.beginPath();
        ctx.moveTo(ox - tick, y);
        ctx.lineTo(ox + tick, y);
        ctx.stroke();
      }
      // labels
      ctx.fillStyle = "#334155";
      ctx.font = "11px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      for (let i = -left; i <= right; i++) {
        if (i === 0) continue;
        ctx.fillText(fmt(i * stepX), ox + i * dx, oy + 6);
      }
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      for (let i = -down; i <= up; i++) {
        if (i === 0) continue;
        ctx.fillText(fmt(i * stepY), ox - 5, oy - i * dy);
      }
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText("0", ox + 6, oy + 6);
      ctx.restore();
    };

    // The ruled background is static per canvas size, so render it once into its
    // own layer and composite it — redrawing ~300 lines on every pointer move is
    // what made the cursor lag once the canvas had grown.
    const getBgCanvas = () => {
      // Same rounding as getInkCanvas() — see the comment there.
      const w = Math.round(W * dpr);
      const h = Math.round(H * dpr);
      if (!bgCanvasRef.current || bgCanvasRef.current.width !== w || bgCanvasRef.current.height !== h) {
        const c = document.createElement("canvas");
        c.width = w;
        c.height = h;
        const bgCtx = c.getContext("2d")!;
        bgCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
        drawRuled(bgCtx);
        bgCanvasRef.current = c;
      }
      return bgCanvasRef.current;
    };

    const drawStroke = (ctx: CanvasRenderingContext2D, stroke: Stroke) => {
      if (stroke.kind === "rect") {
        ctx.globalCompositeOperation = "destination-out";
        const { x1, y1, x2, y2 } = stroke.rect;
        ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
        ctx.globalCompositeOperation = "source-over";
        return;
      }
      if (stroke.kind === "raster") {
        ctx.globalCompositeOperation = "source-over";
        ctx.drawImage(stroke.img, 0, 0, stroke.w, stroke.h);
        return;
      }
      if (stroke.kind === "line") {
        strokeStyleFor(ctx, stroke.tool, stroke.width);
        ctx.beginPath();
        ctx.moveTo(stroke.x1, stroke.y1);
        ctx.lineTo(stroke.x2, stroke.y2);
        ctx.stroke();
        return;
      }
      if (stroke.kind === "curve") {
        strokeStyleFor(ctx, stroke.tool, stroke.width);
        const a = stroke.anchors;
        if (a.length === 1) {
          ctx.beginPath();
          ctx.arc(a[0].x, a[0].y, ctx.lineWidth / 2, 0, Math.PI * 2);
          ctx.fillStyle = ctx.strokeStyle as string;
          ctx.fill();
          return;
        }
        ctx.beginPath();
        ctx.moveTo(a[0].x, a[0].y);
        for (let i = 0; i < a.length - 1; i++) {
          const p0 = a[i];
          const p1 = a[i + 1];
          ctx.bezierCurveTo(p0.hOut.x, p0.hOut.y, p1.hIn.x, p1.hIn.y, p1.x, p1.y);
        }
        ctx.stroke();
        return;
      }
      if (stroke.kind === "ellipse") {
        strokeStyleFor(ctx, stroke.tool, stroke.width);
        ctx.beginPath();
        ctx.ellipse(
          stroke.cx,
          stroke.cy,
          Math.max(1, Math.abs(stroke.rx)),
          Math.max(1, Math.abs(stroke.ry)),
          0,
          0,
          Math.PI * 2
        );
        ctx.stroke();
        return;
      }
      if (stroke.points.length < 1) return;
      strokeStyleFor(ctx, stroke.tool, stroke.width);
      if (stroke.tool === "pen" && stroke.pointerType === "pen") {
        drawPressurePath(ctx, stroke.points, stroke.width);
      } else {
        drawSmoothPath(ctx, stroke.points);
      }
    };

    const replayStrokesToInk = () => {
      const inkCanvas = getInkCanvas();
      const ictx = inkCanvas.getContext("2d")!;
      ictx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ictx.clearRect(0, 0, W, H);
      for (const stroke of strokesRef.current) drawStroke(ictx, stroke);
      ictx.globalCompositeOperation = "source-over";
    };

    const redraw = () => {
      const ctx = canvasRef.current!.getContext("2d")!;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // getBgCanvas()/getInkCanvas() are themselves dpr-scaled (their natural
      // pixel size is W*dpr x H*dpr) — drawing them with an explicit W,H
      // destination size (rather than their natural size) is what keeps this
      // a straight crisp copy instead of scaling by dpr twice.
      ctx.drawImage(getBgCanvas(), 0, 0, W, H);
      if (imageRef.current) {
        const img = imageRef.current;
        const scale = Math.min((W - 32) / img.width, (H - 32) / img.height);
        const w = img.width * scale;
        const h = img.height * scale;
        ctx.drawImage(img, (W - w) / 2, (H - h) / 2, w, h);
        return;
      }
      replayStrokesToInk();
      ctx.drawImage(getInkCanvas(), 0, 0, W, H);
      drawHandles(ctx);
    };

    // Per-move repaint: replay only the in-progress stroke onto the persistent
    // ink layer (opaque pen overdraw / idempotent eraser erase), then composite
    // once per animation frame — O(current stroke) instead of O(all strokes).
    const redrawCurrentStroke = () => {
      rafRef.current = null;
      if (!canvasRef.current) return;
      const ctx = canvasRef.current.getContext("2d")!;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.drawImage(getBgCanvas(), 0, 0, W, H);
      if (imageRef.current) return;
      const stroke = strokesRef.current[strokesRef.current.length - 1];
      if (stroke) {
        const ictx = getInkCanvas().getContext("2d")!;
        ictx.setTransform(dpr, 0, 0, dpr, 0, 0);
        if (stroke.kind === "line" || stroke.kind === "curve" || stroke.kind === "ellipse") {
          // These shapes' geometry changes every move, so overlaying them would
          // leave a trail of stale copies. Replay the committed strokes, then
          // the live shape, for a clean preview — cheap enough because these
          // tools produce few strokes.
          ictx.clearRect(0, 0, W, H);
          for (const s of strokesRef.current.slice(0, -1)) drawStroke(ictx, s);
          drawStroke(ictx, stroke);
        } else {
          drawStroke(ictx, stroke);
        }
      }
      ctx.drawImage(getInkCanvas(), 0, 0, W, H);
    };

    const requestRedraw = () => {
      if (rafRef.current !== null) return;
      rafRef.current = requestAnimationFrame(redrawCurrentStroke);
    };

    const [spaceHeld, setSpaceHeld] = useState(false);
    const panningRef = useRef(false);
    const panStartRef = useRef({ x: 0, y: 0, scrollLeft: 0, scrollTop: 0 });

    // Tablet/touch parity for "hold Space to pan": tracks every active touch
    // pointer so two fingers down switches to pan+pinch-zoom instead of drawing.
    // A pen (stylus) pointer is tracked separately so a resting palm's touch
    // points are ignored while actively writing (basic palm rejection).
    const touchPointersRef = useRef(new Map<number, { x: number; y: number }>());
    const activePenPointerRef = useRef<number | null>(null);
    const pinchRef = useRef<{
      center: { x: number; y: number };
      dist: number;
      scrollLeft: number;
      scrollTop: number;
      zoom: number;
    } | null>(null);

    const touchCenterAndDist = () => {
      const pts = Array.from(touchPointersRef.current.values());
      const cx = (pts[0].x + pts[1].x) / 2;
      const cy = (pts[0].y + pts[1].y) / 2;
      const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      return { center: { x: cx, y: cy }, dist };
    };

    useEffect(() => {
      if (!fullscreen) return;
      const isTextInput = (el: EventTarget | null) => {
        const tag = (el as HTMLElement)?.tagName;
        return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
      };
      const onKeyDown = (e: KeyboardEvent) => {
        if (e.code !== "Space" || isTextInput(e.target)) return;
        e.preventDefault();
        setSpaceHeld(true);
      };
      const onKeyUp = (e: KeyboardEvent) => {
        if (e.code !== "Space") return;
        setSpaceHeld(false);
      };
      // Safety net: if the keyup is ever missed (focus jumps to a native
      // dropdown/OS dialog mid-hold, tab switch, etc.), space-pan mode would
      // otherwise latch "on" forever and every future click would pan instead
      // of draw — with no error to explain why the pen "stopped working".
      const onBlur = () => setSpaceHeld(false);
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("keyup", onKeyUp);
      window.addEventListener("blur", onBlur);
      return () => {
        window.removeEventListener("keydown", onKeyDown);
        window.removeEventListener("keyup", onKeyUp);
        window.removeEventListener("blur", onBlur);
      };
    }, [fullscreen]);

    const grownRef = useRef({ top: 0, left: 0 });
    const growingRef = useRef(false);
    // useLayoutEffect (not useEffect) is what makes this seamless: it runs
    // synchronously right after the resized canvas is committed to the DOM but
    // BEFORE the browser paints, so the repaint and the compensating scroll
    // land in the same frame the user ever sees. A plain useEffect runs after
    // paint, which left a real (if brief) frame where the shifted content was
    // visible before the scroll caught up — that flash was the bug.
    useLayoutEffect(() => {
      redraw();
      const g = grownRef.current;
      const wrapper = wrapperRef.current;
      if (wrapper && (g.top || g.left)) {
        // Absolute scrollTo (reading scroll position fresh, right now) rather
        // than a relative scrollBy — if anything nudged the wrapper's scroll
        // between when this grow was queued and this effect actually running
        // (iOS rubber-band/momentum from the gesture that just ended, however
        // brief), a relative delta would compound that drift instead of
        // landing on the correct absolute position. `behavior: "instant"`
        // rules out any inherited smooth-scroll animating the correction
        // where the user can see it happen.
        wrapper.scrollTo({
          top: wrapper.scrollTop + g.top * zoom,
          left: wrapper.scrollLeft + g.left * zoom,
          behavior: "instant",
        });
        grownRef.current = { top: 0, left: 0 };
      }
      growingRef.current = false;
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [canvasWidth, canvasHeight]);

    const shiftStrokesX = (dx: number) => {
      for (const s of strokesRef.current) {
        if (s.kind === "rect") {
          s.rect.x1 += dx;
          s.rect.x2 += dx;
        } else if (s.kind === "path") {
          for (const p of s.points) p.x += dx;
        } else if (s.kind === "line") {
          s.x1 += dx;
          s.x2 += dx;
        } else if (s.kind === "curve") {
          for (const a of s.anchors) {
            a.x += dx;
            a.hIn.x += dx;
            a.hOut.x += dx;
          }
        } else if (s.kind === "ellipse") {
          s.cx += dx;
        }
        // "raster" strokes (restored old work) stay pinned at their original
        // (0,0) origin — they're a flattened snapshot of the page as it was,
        // not something meaningful to translate piecemeal.
      }
      for (const s of redoStackRef.current) {
        if (s.kind === "rect") {
          s.rect.x1 += dx;
          s.rect.x2 += dx;
        } else if (s.kind === "path") {
          for (const p of s.points) p.x += dx;
        } else if (s.kind === "line") {
          s.x1 += dx;
          s.x2 += dx;
        } else if (s.kind === "curve") {
          for (const a of s.anchors) {
            a.x += dx;
            a.hIn.x += dx;
            a.hOut.x += dx;
          }
        } else if (s.kind === "ellipse") {
          s.cx += dx;
        }
      }
      if (gridRef.current) {
        gridRef.current.ox += dx;
        bgCanvasRef.current = null;
      }
    };

    const getPos = (clientX: number, clientY: number, pressure?: number): Point => {
      const rect = canvasRef.current!.getBoundingClientRect();
      return {
        x: ((clientX - rect.left) / rect.width) * W,
        y: ((clientY - rect.top) / rect.height) * H,
        pressure,
      };
    };

    // Left-growth needed while a stroke is still in progress, applied once
    // that stroke ends (see the comment in maybeGrow for why).
    const pendingGrowLeftRef = useRef(0);

    const applyGrowLeft = (growLeft: number) => {
      growingRef.current = true;
      shiftStrokesX(growLeft);
      grownRef.current = { top: 0, left: growLeft };
      setCanvasWidth((w) => Math.min(MAX_WIDTH, w + growLeft));
    };

    const maybeGrow = (p: Point) => {
      if (!fullscreen || growingRef.current) return;

      const growH = H - p.y <= GROW_THRESHOLD && H < MAX_HEIGHT ? Math.min(GROW_CHUNK, MAX_HEIGHT - H) : 0;
      const growRight = W - p.x <= GROW_THRESHOLD && W < MAX_WIDTH ? Math.min(GROW_CHUNK, MAX_WIDTH - W) : 0;
      let growLeft = !growRight && p.x <= GROW_THRESHOLD && W < MAX_WIDTH ? Math.min(GROW_CHUNK, MAX_WIDTH - W) : 0;

      if (growLeft && drawing.current) {
        // Growing left means shifting every existing point (including the
        // stroke currently being drawn) AND scrolling the viewport to
        // compensate — doing both while a pointer is actively down changes
        // the DOM/layout under it mid-gesture, which iOS Safari (and others)
        // can respond to by cancelling the touch/pen sequence outright. That's
        // exactly what "writing near the left edge drags me to the middle,
        // then the pen stops drawing until I lift it" was: the shift raced
        // ahead of the pen's own next point (producing the stray jump-line),
        // and the resulting scroll cancelled the pointer stream (silently
        // killing the rest of that stroke). Deferring to pointerup avoids
        // both — nothing is lost, ink drawn past the current left edge in the
        // meantime just isn't visible until the deferred grow lands.
        pendingGrowLeftRef.current = Math.max(pendingGrowLeftRef.current, growLeft);
        growLeft = 0;
      }

      if (!growH && !growRight && !growLeft) return;
      growingRef.current = true;

      if (growLeft) shiftStrokesX(growLeft);
      // Only left-growth needs scroll compensation (it relocates existing ink).
      // Bottom/right growth keeps the view exactly where the user is — no auto
      // scroll, so the pen never gets dragged into the new space mid-stroke.
      grownRef.current = { top: 0, left: growLeft };

      if (growH) setCanvasHeight((h) => Math.min(MAX_HEIGHT, h + growH));
      if (growRight || growLeft) setCanvasWidth((w) => Math.min(MAX_WIDTH, w + (growRight || growLeft)));
    };

    const beginPan = (e: React.PointerEvent) => {
      panningRef.current = true;
      panStartRef.current = {
        x: e.clientX,
        y: e.clientY,
        scrollLeft: wrapperRef.current?.scrollLeft ?? 0,
        scrollTop: wrapperRef.current?.scrollTop ?? 0,
      };
    };

    const moveGridTo = (ox: number, oy: number) => {
      if (!gridRef.current || imageRef.current) return;
      gridRef.current.ox = ox;
      gridRef.current.oy = oy;
      bgCanvasRef.current = null;
      redraw();
      onChange?.();
    };

    // Snap a point to the nearest grid intersection when a grid is active.
    const snapToGrid = (p: Point): Point => {
      const g = gridRef.current;
      if (!g) return p;
      const dx = g.stepX * g.scale;
      const dy = g.stepY * g.scale;
      if (dx <= 0 || dy <= 0) return p;
      return {
        x: g.ox + Math.round((p.x - g.ox) / dx) * dx,
        y: g.oy - Math.round((g.oy - p.y) / dy) * dy,
      };
    };

    // The sample farthest from the straight line A→B — used as the bend point
    // of a curve being dragged out (so the curve bows where you deviated most).
    const farthestFromSegment = (samples: Point[], a: Point, b: Point) => {
      let best = a;
      let bestDist = 0;
      const len = Math.hypot(b.x - a.x, b.y - a.y);
      for (const s of samples) {
        let d: number;
        if (len < 1e-6) {
          d = Math.hypot(s.x - a.x, s.y - a.y);
        } else {
          const t = Math.max(0, Math.min(1, ((s.x - a.x) * (b.x - a.x) + (s.y - a.y) * (b.y - a.y)) / (len * len)));
          const px = a.x + t * (b.x - a.x);
          const py = a.y + t * (b.y - a.y);
          d = Math.hypot(s.x - px, s.y - py);
        }
        if (d > bestDist) {
          bestDist = d;
          best = s;
        }
      }
      return best;
    };

    // ---- Editable-shape helpers (Select tool + post-draw manipulation) ----

    const HANDLE_HIT = 10;
    const ANCHOR_HIT = 9;
    const HANDLE_COLOR = "#0ea5e9";
    const HOVER_COLOR = "#94a3b8";

    // Smooth (Catmull-Rom) control handles for anchor i of a point list.
    const autoHandles = (pts: { x: number; y: number }[], i: number) => {
      const n = pts.length;
      const p = pts[i];
      if (n === 1) return { hIn: { ...p }, hOut: { ...p } };
      if (i === 0) {
        const d = { x: (pts[1].x - pts[0].x) / 3, y: (pts[1].y - pts[0].y) / 3 };
        return { hIn: { x: p.x, y: p.y }, hOut: { x: p.x + d.x, y: p.y + d.y } };
      }
      if (i === n - 1) {
        const d = { x: (pts[n - 1].x - pts[n - 2].x) / 3, y: (pts[n - 1].y - pts[n - 2].y) / 3 };
        return { hIn: { x: p.x - d.x, y: p.y - d.y }, hOut: { x: p.x, y: p.y } };
      }
      const a = pts[i - 1];
      const b = pts[i + 1];
      const m = { x: (b.x - a.x) / 6, y: (b.y - a.y) / 6 };
      return { hIn: { x: p.x - m.x, y: p.y - m.y }, hOut: { x: p.x + m.x, y: p.y + m.y } };
    };

    // Downsample a freehand drag into a smooth editable anchor path.
    const buildAnchorsFromPath = (points: Point[]): Anchor[] => {
      if (points.length === 0) return [];
      const minDist = 14;
      const kept: Point[] = [points[0]];
      for (let i = 1; i < points.length; i++) {
        const l = kept[kept.length - 1];
        if (Math.hypot(points[i].x - l.x, points[i].y - l.y) >= minDist) kept.push(points[i]);
      }
      if (kept.length === 1) {
        const last = points[points.length - 1];
        if (Math.hypot(last.x - kept[0].x, last.y - kept[0].y) > 1) kept.push(last);
      }
      let pts = kept;
      const MAX = 80;
      if (pts.length > MAX) {
        const step = (pts.length - 1) / (MAX - 1);
        const out = [pts[0]];
        for (let i = 1; i < MAX - 1; i++) out.push(pts[Math.round(i * step)]);
        out.push(pts[pts.length - 1]);
        pts = out;
      }
      return pts.map((p, i) => {
        const h = autoHandles(pts, i);
        return { x: p.x, y: p.y, hIn: h.hIn, hOut: h.hOut };
      });
    };

    const distToSeg = (px: number, py: number, ax: number, ay: number, bx: number, by: number) => {
      const dx = bx - ax;
      const dy = by - ay;
      const len2 = dx * dx + dy * dy;
      const t = len2 < 1e-9 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / len2));
      return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
    };

    const bezierPoint = (p0: Point, p1: Point, p2: Point, p3: Point, t: number) => {
      const u = 1 - t;
      const a = u * u * u;
      const b = 3 * u * u * t;
      const c = 3 * u * t * t;
      const d = t * t * t;
      return { x: a * p0.x + b * p1.x + c * p2.x + d * p3.x, y: a * p0.y + b * p1.y + c * p2.y + d * p3.y };
    };

    // Sampled polyline of a curve stroke (for hit-testing / insertion).
    const curvePolyline = (stroke: CurveStroke, steps = 14): Point[] => {
      const a = stroke.anchors;
      const pts: Point[] = [{ x: a[0].x, y: a[0].y }];
      for (let i = 0; i < a.length - 1; i++) {
        const p0 = a[i];
        const p1 = a[i + 1];
        for (let s = 1; s <= steps; s++) {
          const t = s / steps;
          pts.push(bezierPoint(p0, p0.hOut, p1.hIn, p1, t));
        }
      }
      return pts;
    };

    const distanceToCurve = (stroke: CurveStroke, p: Point) => {
      const poly = curvePolyline(stroke, 12);
      let best = Infinity;
      for (let i = 0; i < poly.length - 1; i++) {
        best = Math.min(best, distToSeg(p.x, p.y, poly[i].x, poly[i].y, poly[i + 1].x, poly[i + 1].y));
      }
      return best;
    };

    // Projection parameter of p onto segment a→b (clamped 0..1).
    const projT = (a: Point, b: Point, p: Point) => {
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const len2 = dx * dx + dy * dy;
      if (len2 < 1e-9) return 0;
      return Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2));
    };

    // Nearest point on the curve to p (used to preview where a double-click
    // would spawn a new anchor).
    const nearestPointOnCurve = (stroke: CurveStroke, p: Point): Point => {
      const poly = curvePolyline(stroke, 16);
      let best: Point = { x: p.x, y: p.y };
      let bestD = Infinity;
      for (let i = 0; i < poly.length - 1; i++) {
        const t = projT(poly[i], poly[i + 1], p);
        const qx = poly[i].x + t * (poly[i + 1].x - poly[i].x);
        const qy = poly[i].y + t * (poly[i + 1].y - poly[i].y);
        const d = Math.hypot(p.x - qx, p.y - qy);
        if (d < bestD) {
          bestD = d;
          best = { x: qx, y: qy };
        }
      }
      return best;
    };

    const pointInEllipse = (stroke: EllipseStroke, p: Point) => {
      const rx = Math.abs(stroke.rx);
      const ry = Math.abs(stroke.ry);
      if (rx < 1 || ry < 1) return Math.hypot(p.x - stroke.cx, p.y - stroke.cy) <= HANDLE_HIT;
      const nx = (p.x - stroke.cx) / rx;
      const ny = (p.y - stroke.cy) / ry;
      return nx * nx + ny * ny <= 1;
    };

    const distanceToEllipse = (stroke: EllipseStroke, p: Point) => {
      const rx = Math.abs(stroke.rx);
      const ry = Math.abs(stroke.ry);
      if (rx < 1 || ry < 1) return Math.hypot(p.x - stroke.cx, p.y - stroke.cy);
      const ang = Math.atan2(p.y - stroke.cy, p.x - stroke.cx);
      const ex = stroke.cx + rx * Math.cos(ang);
      const ey = stroke.cy + ry * Math.sin(ang);
      return Math.hypot(p.x - ex, p.y - ey);
    };

    const shapeHit = (stroke: Stroke, p: Point) => {
      if (stroke.kind === "ellipse") {
        return pointInEllipse(stroke, p) || distanceToEllipse(stroke, p) <= Math.max(stroke.width / 2, 2) + HANDLE_HIT;
      }
      if (stroke.kind === "curve") {
        return distanceToCurve(stroke, p) <= Math.max(stroke.width / 2, 2) + HANDLE_HIT;
      }
      return false;
    };

    // Topmost shape under a point (only curves / ellipses are selectable).
    const hitTestShape = (p: Point): number | null => {
      for (let i = strokesRef.current.length - 1; i >= 0; i--) {
        const s = strokesRef.current[i];
        if ((s.kind === "curve" || s.kind === "ellipse") && shapeHit(s, p)) return i;
      }
      return null;
    };

    const ellipseCorners = (s: EllipseStroke) => {
      const rx = s.rx;
      const ry = s.ry;
      return [
        [s.cx - rx, s.cy - ry],
        [s.cx + rx, s.cy - ry],
        [s.cx + rx, s.cy + ry],
        [s.cx - rx, s.cy + ry],
      ] as [number, number][];
    };

    // Diagonal resize cursor for an ellipse bounding-box corner (0=TL,1=TR,2=BR,3=BL).
    const cornerCursor = (index: number) => (index % 2 === 0 ? "nwse-resize" : "nesw-resize");

    // Which handle (if any) of the selected shape is under p.
    const hitTestHandle = (stroke: Stroke, p: Point): EditState | null => {
      if (stroke.kind === "curve") {
        for (let i = 0; i < stroke.anchors.length; i++) {
          const a = stroke.anchors[i];
          if (Math.hypot(a.hIn.x - a.x, a.hIn.y - a.y) > 0.5 && Math.hypot(p.x - a.hIn.x, p.y - a.hIn.y) <= HANDLE_HIT)
            return { mode: "hIn", index: i, px: p.x, py: p.y };
          if (Math.hypot(a.hOut.x - a.x, a.hOut.y - a.y) > 0.5 && Math.hypot(p.x - a.hOut.x, p.y - a.hOut.y) <= HANDLE_HIT)
            return { mode: "hOut", index: i, px: p.x, py: p.y };
        }
        for (let i = 0; i < stroke.anchors.length; i++) {
          const a = stroke.anchors[i];
          if (Math.hypot(p.x - a.x, p.y - a.y) <= ANCHOR_HIT) return { mode: "anchor", index: i, px: p.x, py: p.y };
        }
      } else if (stroke.kind === "ellipse") {
        const c = ellipseCorners(stroke);
        for (let i = 0; i < 4; i++) {
          if (Math.hypot(p.x - c[i][0], p.y - c[i][1]) <= HANDLE_HIT) return { mode: "corner", index: i, px: p.x, py: p.y };
        }
      }
      return null;
    };

    // Apply an edit delta (current pointer minus start) to a cloned stroke.
    const applyEditDelta = (ns: Stroke, ed: EditState, dx: number, dy: number) => {
      if (ns.kind === "curve") {
        if (ed.mode === "move") {
          for (const a of ns.anchors) {
            a.x += dx; a.y += dy; a.hIn.x += dx; a.hIn.y += dy; a.hOut.x += dx; a.hOut.y += dy;
          }
        } else if (ed.mode === "anchor") {
          const a = ns.anchors[ed.index];
          a.x += dx; a.y += dy; a.hIn.x += dx; a.hIn.y += dy; a.hOut.x += dx; a.hOut.y += dy;
        } else if (ed.mode === "hIn") {
          const a = ns.anchors[ed.index];
          a.hIn.x += dx; a.hIn.y += dy;
        } else if (ed.mode === "hOut") {
          const a = ns.anchors[ed.index];
          a.hOut.x += dx; a.hOut.y += dy;
        }
      } else if (ns.kind === "ellipse") {
        if (ed.mode === "move") {
          ns.cx += dx; ns.cy += dy;
        } else if (ed.mode === "corner") {
          const c = ellipseCorners(ns);
          const f = c[(ed.index + 2) % 4];
          const draggedX = c[ed.index][0] + dx;
          const draggedY = c[ed.index][1] + dy;
          ns.cx = (f[0] + draggedX) / 2;
          ns.cy = (f[1] + draggedY) / 2;
          ns.rx = (draggedX - f[0]) / 2;
          ns.ry = (draggedY - f[1]) / 2;
        }
      }
    };

    // Insert a new anchor on the curve nearest to p, keeping it smooth.
    const insertAnchorAt = (stroke: CurveStroke, p: Point) => {
      const a = stroke.anchors;
      if (a.length < 2) return false;
      const steps = 16;
      const poly = curvePolyline(stroke, steps);
      let bestI = 0;
      let bestT = 0;
      let bestD = Infinity;
      for (let i = 0; i < poly.length - 1; i++) {
        const dx = poly[i + 1].x - poly[i].x;
        const dy = poly[i + 1].y - poly[i].y;
        const len2 = dx * dx + dy * dy;
        let t = len2 < 1e-9 ? 0 : ((p.x - poly[i].x) * dx + (p.y - poly[i].y) * dy) / len2;
        t = Math.max(0, Math.min(1, t));
        const qx = poly[i].x + t * dx;
        const qy = poly[i].y + t * dy;
        const d = Math.hypot(p.x - qx, p.y - qy);
        if (d < bestD) { bestD = d; bestI = i; bestT = t; }
      }
      const seg = Math.floor(bestI / steps);
      const localT = (bestI - seg * steps) / steps + bestT / steps;
      const A = a[seg];
      const B = a[seg + 1];
      const np = bezierPoint(A, A.hOut, B.hIn, B, localT);
      const newAnchors = a.slice(0, seg + 1).concat([{ x: np.x, y: np.y, hIn: { x: np.x, y: np.y }, hOut: { x: np.x, y: np.y } }], a.slice(seg + 1));
      stroke.anchors = newAnchors.map((an, i) => {
        const h = autoHandles(newAnchors, i);
        return { x: an.x, y: an.y, hIn: h.hIn, hOut: h.hOut };
      });
      return true;
    };

    const strokeGeomEqual = (a: Stroke | null, b: Stroke | null) => {
      if (!a || !b) return false;
      if (a.kind !== b.kind) return false;
      return JSON.stringify(a) === JSON.stringify(b);
    };

    const drawHandleDot = (ctx: CanvasRenderingContext2D, x: number, y: number, color: string) => {
      ctx.fillStyle = color;
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(x, y, 4.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    };

    // Render the hover (light) or selected (full) control points for a shape.
    const drawShapePoints = (ctx: CanvasRenderingContext2D, stroke: Stroke, selected: boolean) => {
      ctx.save();
      if (stroke.kind === "ellipse") {
        const rx = stroke.rx;
        const ry = stroke.ry;
        if (selected) {
          ctx.strokeStyle = "rgba(14,165,233,0.5)";
          ctx.setLineDash([5, 4]);
          ctx.lineWidth = 1;
          ctx.strokeRect(stroke.cx - rx, stroke.cy - ry, rx * 2, ry * 2);
          ctx.setLineDash([]);
        }
        const c = ellipseCorners(stroke);
        for (const corner of c) drawHandleDot(ctx, corner[0], corner[1], selected ? HANDLE_COLOR : HOVER_COLOR);
        if (selected) drawHandleDot(ctx, stroke.cx, stroke.cy, HANDLE_COLOR);
      } else if (stroke.kind === "curve") {
        const a = stroke.anchors;
        if (selected) {
          ctx.strokeStyle = "rgba(14,165,233,0.6)";
          ctx.lineWidth = 1;
          for (const an of a) {
            if (Math.hypot(an.hIn.x - an.x, an.hIn.y - an.y) > 0.5) {
              ctx.beginPath();
              ctx.moveTo(an.x, an.y);
              ctx.lineTo(an.hIn.x, an.hIn.y);
              ctx.stroke();
            }
            if (Math.hypot(an.hOut.x - an.x, an.hOut.y - an.y) > 0.5) {
              ctx.beginPath();
              ctx.moveTo(an.x, an.y);
              ctx.lineTo(an.hOut.x, an.hOut.y);
              ctx.stroke();
            }
          }
        }
        for (const an of a) {
          ctx.fillStyle = "#ffffff";
          ctx.strokeStyle = selected ? HANDLE_COLOR : HOVER_COLOR;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.rect(an.x - 4, an.y - 4, 8, 8);
          ctx.fill();
          ctx.stroke();
        }
        if (selected) {
          for (const an of a) {
            if (Math.hypot(an.hIn.x - an.x, an.hIn.y - an.y) > 0.5) drawHandleDot(ctx, an.hIn.x, an.hIn.y, HANDLE_COLOR);
            if (Math.hypot(an.hOut.x - an.x, an.hOut.y - an.y) > 0.5) drawHandleDot(ctx, an.hOut.x, an.hOut.y, HANDLE_COLOR);
          }
        }
      }
      ctx.restore();
    };

    const drawHandles = (ctx: CanvasRenderingContext2D) => {
      const hover = hoverIndexRef.current;
      const sel = selectedRef.current;
      if (hover != null && hover !== sel) {
        const s = strokesRef.current[hover];
        if (s) drawShapePoints(ctx, s, false);
      }
      if (sel != null) {
        const s = strokesRef.current[sel];
        if (s) drawShapePoints(ctx, s, true);
      }
      // Ghost insertion point: while hovering a curve in Select mode (and not
      // actively dragging a handle), preview where a double-click would spawn a
      // new anchor.
      if (toolRef.current === "select" && !editingRef.current && hoverPointRef.current) {
        const hp = hoverPointRef.current;
        const targetIdx = sel != null ? sel : hover;
        if (targetIdx != null) {
          const s = strokesRef.current[targetIdx];
          if (s && s.kind === "curve" && s.anchors.length >= 2) {
            const near = distanceToCurve(s, hp) <= Math.max(s.width / 2, 2) + HANDLE_HIT;
            if (near) {
              const q = nearestPointOnCurve(s, hp);
              const onAnchor = s.anchors.some((a) => Math.hypot(a.x - q.x, a.y - q.y) <= ANCHOR_HIT);
              if (!onAnchor) {
                ctx.save();
                ctx.fillStyle = "rgba(14,165,233,0.18)";
                ctx.strokeStyle = "rgba(14,165,233,0.85)";
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.arc(q.x, q.y, 5, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();
                ctx.restore();
              }
            }
          }
        }
      }
    };

    const beginEdit = (state: EditState, e: React.PointerEvent) => {
      editingRef.current = state;
      hoverPointRef.current = null;
      editSnapshotRef.current = selectedRef.current != null ? cloneStrokeDeep(strokesRef.current[selectedRef.current]) : null;
      redoStackRef.current = [];
      (e.target as Element).setPointerCapture?.(e.pointerId);
    };

    const handleEditMove = (e: React.PointerEvent) => {
      const ed = editingRef.current;
      if (!ed) return;
      const p = getPos(e.clientX, e.clientY, e.pressure);
      const dx = p.x - ed.px;
      const dy = p.y - ed.py;
      const snap = editSnapshotRef.current;
      const sel = selectedRef.current;
      if (snap && sel != null) {
        const ns = cloneStrokeDeep(snap);
        applyEditDelta(ns, ed, dx, dy);
        strokesRef.current[sel] = ns;
      }
      redraw();
      e.preventDefault();
    };

    const handleSelectDown = (e: React.PointerEvent) => {
      const p = getPos(e.clientX, e.clientY, e.pressure);
      const target = e.target as Element;
      target.setPointerCapture?.(e.pointerId);

      // Double-tap / double-click: edit anchors on a curve.
      const now = performance.now();
      const dbl = now - lastTapRef.current.t < 350 && Math.hypot(p.x - lastTapRef.current.x, p.y - lastTapRef.current.y) < 8;
      lastTapRef.current = { t: now, x: p.x, y: p.y };
      if (dbl) {
        const idx = hitTestShape(p);
        if (idx != null) {
          const s = strokesRef.current[idx];
          if (s.kind === "curve") {
            const ai = s.anchors.findIndex((a) => Math.hypot(p.x - a.x, p.y - a.y) <= ANCHOR_HIT);
            if (ai >= 0 && s.anchors.length > 2) {
              s.anchors.splice(ai, 1);
              selectedRef.current = idx;
              onChange?.();
              redraw();
              return;
            }
            if (insertAnchorAt(s, p)) {
              selectedRef.current = idx;
              onChange?.();
              redraw();
              return;
            }
          }
        }
      }

      // 1) A control handle of the currently selected shape.
      if (selectedRef.current != null) {
        const s = strokesRef.current[selectedRef.current];
        const h = hitTestHandle(s, p);
        if (h) {
          beginEdit(h, e);
          return;
        }
      }
      // 2) Any shape under the cursor → select it (and maybe grab it).
      const idx = hitTestShape(p);
      if (idx != null) {
        selectedRef.current = idx;
        const s = strokesRef.current[idx];
        const h = hitTestHandle(s, p);
        if (h) {
          beginEdit(h, e);
        } else if (shapeHit(s, p)) {
          beginEdit({ mode: "move", index: 0, px: p.x, py: p.y }, e);
        }
        redraw();
        return;
      }
      // 3) Empty space → deselect.
      if (selectedRef.current != null) {
        selectedRef.current = null;
        redraw();
      }
    };

    const start = (e: React.PointerEvent) => {
      updateCursor(e.clientX, e.clientY);

      // Axes edit mode: drag to pan the origin (pinch zooms, handled in move).
      if (toolRef.current === "axes") {
        const p = getPos(e.clientX, e.clientY, e.pressure);
        if (e.pointerType === "touch") {
          (e.target as Element).setPointerCapture?.(e.pointerId);
          touchPointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
          if (touchPointersRef.current.size === 2) {
            const { center, dist } = touchCenterAndDist();
            pinchRef.current = { center, dist, scrollLeft: 0, scrollTop: 0, zoom: gridRef.current?.scale ?? 40 };
            return;
          }
        }
        gridPanRef.current = {
          px: p.x,
          py: p.y,
          ox: gridRef.current?.ox ?? p.x,
          oy: gridRef.current?.oy ?? p.y,
        };
        (e.target as Element).setPointerCapture?.(e.pointerId);
        return;
      }

      if (toolRef.current === "select") {
        e.preventDefault();
        if (e.pointerType === "pen" || e.pointerType === "mouse") activePenPointerRef.current = e.pointerId;
        handleSelectDown(e);
        return;
      }

      if (e.pointerType === "touch" && (toolRef.current as CanvasTool) !== "select") {
        (e.target as Element).setPointerCapture?.(e.pointerId);
        touchPointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (touchPointersRef.current.size === 2) {
          // Second finger down: switch to two-finger pan + pinch-zoom, the
          // touch equivalent of desktop's "hold Space to pan" / scroll-wheel
          // zoom. (A lone finger never reaches `drawing.current`, below, so
          // there's never a stray stroke to cancel here.)
          panningRef.current = false;
          const { center, dist } = touchCenterAndDist();
          pinchRef.current = {
            center,
            dist,
            scrollLeft: wrapperRef.current?.scrollLeft ?? 0,
            scrollTop: wrapperRef.current?.scrollTop ?? 0,
            zoom,
          };
          return;
        }
        if (touchPointersRef.current.size > 2) return;
        // Palm rejection: a lone finger contact is always treated as a
        // resting palm (or an accidental touch), never a drawing input — it's
        // tracked above purely so a second finger can still start a pinch/pan.
        // This app is written with a stylus (Apple Pencil, below); the
        // alternative — trusting a single touch until we've "seen" a pen —
        // has an unavoidable race: a palm that lands a moment before the
        // pencil first touches down already started drawing before we could
        // tell, and normal handwriting posture means the palm often *does*
        // land first.
        return;
      }

      if (spaceHeld) {
        (e.target as Element).setPointerCapture?.(e.pointerId);
        beginPan(e);
        return;
      }
      if (imageRef.current) return;
      if (pinchRef.current) return;
      e.preventDefault();
      if (e.pointerType === "pen") activePenPointerRef.current = e.pointerId;
      drawing.current = true;
      drawingPointerIdRef.current = e.pointerId;
      selectedRef.current = null;
      hoverIndexRef.current = null;
      const p = getPos(e.clientX, e.clientY, e.pressure);
      const width = toolRef.current === "eraser" ? eraserWidthRef.current : penWidthRef.current;
      redoStackRef.current = [];
      if (toolRef.current === "ruler") {
        const sp = snapToGrid(p);
        strokesRef.current.push({
          kind: "line",
          x1: sp.x,
          y1: sp.y,
          x2: sp.x,
          y2: sp.y,
          tool: "ruler",
          width: penWidthRef.current,
        });
      } else if (toolRef.current === "curve") {
        // Start as a simple 2-point segment; more anchors are added afterwards
        // (double-click a segment) once it's selected.
        curvePathRef.current = [p];
        const h0 = autoHandles([p, p], 0);
        const h1 = autoHandles([p, p], 1);
        strokesRef.current.push({
          kind: "curve",
          tool: "curve",
          anchors: [
            { x: p.x, y: p.y, hIn: h0.hIn, hOut: h0.hOut },
            { x: p.x, y: p.y, hIn: h1.hIn, hOut: h1.hOut },
          ],
          width: penWidthRef.current,
        });
      } else if (toolRef.current === "ellipse") {
        ellipseStartRef.current = p;
        strokesRef.current.push({
          kind: "ellipse",
          cx: p.x,
          cy: p.y,
          rx: 0,
          ry: 0,
          tool: "ellipse",
          width: penWidthRef.current,
        });
      } else {
        strokesRef.current.push({
          kind: "path",
          points: [p],
          tool: toolRef.current,
          width,
          pointerType: e.pointerType,
        });
      }
      redraw();
      maybeGrow(p);
    };

    const move = (e: React.PointerEvent) => {
      updateCursor(e.clientX, e.clientY);
      if (e.pointerType === "touch" && touchPointersRef.current.has(e.pointerId)) {
        touchPointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
      }

      if (editingRef.current) {
        handleEditMove(e);
        return;
      }

      // Axes mode: pinch zooms the grid scale, drag pans the origin.
      if (toolRef.current === "axes") {
        if (pinchRef.current && touchPointersRef.current.size === 2) {
          const { dist } = touchCenterAndDist();
          const pinchStart = pinchRef.current;
          if (gridRef.current) {
            const ns = Math.min(200, Math.max(10, gridRef.current.scale * (dist / pinchStart.dist)));
            if (ns !== gridRef.current.scale) {
              gridRef.current.scale = ns;
              bgCanvasRef.current = null;
              redraw();
              onChange?.();
            }
          }
          return;
        }
        if (gridPanRef.current) {
          const p = getPos(e.clientX, e.clientY, e.pressure);
          moveGridTo(
            gridPanRef.current.ox + (p.x - gridPanRef.current.px),
            gridPanRef.current.oy + (p.y - gridPanRef.current.py)
          );
        }
        return;
      }

      if (pinchRef.current && touchPointersRef.current.size === 2) {
        const { center, dist } = touchCenterAndDist();
        const pinchStart = pinchRef.current;
        const wrapper = wrapperRef.current;
        if (wrapper) {
          const newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, pinchStart.zoom * (dist / pinchStart.dist)));
          onZoomChange?.(Math.round(newZoom * 100) / 100);
          wrapper.scrollLeft = pinchStart.scrollLeft - (center.x - pinchStart.center.x);
          wrapper.scrollTop = pinchStart.scrollTop - (center.y - pinchStart.center.y);
        }
        return;
      }

      if (panningRef.current) {
        if (wrapperRef.current) {
          wrapperRef.current.scrollLeft = panStartRef.current.scrollLeft - (e.clientX - panStartRef.current.x);
          wrapperRef.current.scrollTop = panStartRef.current.scrollTop - (e.clientY - panStartRef.current.y);
        }
        return;
      }
      // Only the pointer that actually started this stroke may extend it —
      // Select-tool hover: reveal a shape's points as the cursor passes over it.
      if (toolRef.current === "select" && !editingRef.current) {
        const hp = getPos(e.clientX, e.clientY, e.pressure);
        const idx = hitTestShape(hp);
        const prev = hoverPointRef.current;
        const moved = !prev || prev.x !== hp.x || prev.y !== hp.y;
        hoverPointRef.current = hp;
        if (idx !== hoverIndexRef.current || moved) {
          hoverIndexRef.current = idx;
          redraw();
        }
        return;
      }

      // otherwise an unrelated second pointer (a resting palm generating its
      // own move events) would splice its coordinates into someone else's ink.
      if (!drawing.current || e.pointerId !== drawingPointerIdRef.current) return;
      e.preventDefault();
      const stroke = strokesRef.current[strokesRef.current.length - 1];
      // A stylus can sample at a much higher rate than pointermove fires;
      // getCoalescedEvents() recovers those in-between samples so fast
      // strokes stay smooth instead of turning into short straight segments.
      const native = e.nativeEvent as PointerEvent;
      const coalesced = native.getCoalescedEvents?.() ?? [];
      const events = coalesced.length ? coalesced : [native];
      let p: Point = getPos(e.clientX, e.clientY, e.pressure);
      if (stroke.kind === "line") {
        p = getPos(e.clientX, e.clientY, e.pressure);
        const sp = snapToGrid(p);
        stroke.x2 = sp.x;
        stroke.y2 = sp.y;
      } else if (stroke.kind === "curve") {
        p = getPos(e.clientX, e.clientY, e.pressure);
        const s = curvePathRef.current[0];
        const a0 = autoHandles([s, p], 0);
        const a1 = autoHandles([s, p], 1);
        stroke.anchors = [
          { x: s.x, y: s.y, hIn: a0.hIn, hOut: a0.hOut },
          { x: p.x, y: p.y, hIn: a1.hIn, hOut: a1.hOut },
        ];
      } else if (stroke.kind === "ellipse") {
        p = getPos(e.clientX, e.clientY, e.pressure);
        const s = ellipseStartRef.current ?? p;
        stroke.cx = (s.x + p.x) / 2;
        stroke.cy = (s.y + p.y) / 2;
        stroke.rx = (p.x - s.x) / 2;
        stroke.ry = (p.y - s.y) / 2;
      } else if (stroke.kind === "path") {
        for (const ev of events) {
          p = getPos(ev.clientX, ev.clientY, ev.pressure);
          stroke.points.push(p);
        }
      }
      requestRedraw();
      maybeGrow(p);
    };

    const end = (e: React.PointerEvent) => {
      // Finishing a shape-handle / move edit: commit one undo step.
      if (editingRef.current) {
        const ed = editingRef.current;
        editingRef.current = null;
        const sel = selectedRef.current;
        const snap = editSnapshotRef.current;
        if (snap && sel != null) {
          const cur = strokesRef.current[sel];
          if (!strokeGeomEqual(snap, cur)) redoStackRef.current.push(snap);
        }
        editSnapshotRef.current = null;
        onChange?.();
        redraw();
        return;
      }

      gridPanRef.current = null;
      curveSamplesRef.current = [];
      ellipseStartRef.current = null;
      if (e.pointerType === "touch") {
        touchPointersRef.current.delete(e.pointerId);
        if (touchPointersRef.current.size < 2) pinchRef.current = null;
      }
      if (activePenPointerRef.current === e.pointerId) activePenPointerRef.current = null;

      if (panningRef.current) {
        panningRef.current = false;
        return;
      }
      // Same reasoning as move(): an unrelated pointer lifting (a palm,
      // mid-stroke) must not end someone else's in-progress stroke.
      if (!drawing.current || e.pointerId !== drawingPointerIdRef.current) return;
      drawing.current = false;
      drawingPointerIdRef.current = null;
      onChange?.();

      // A freshly-drawn curve/ellipse stays selected with handles showing, and
      // the toolbar switches to the Select tool (Photoshop-style) so the shape
      // can be tweaked immediately.
      const lastStroke = strokesRef.current[strokesRef.current.length - 1];
      if (lastStroke && (lastStroke.kind === "curve" || lastStroke.kind === "ellipse")) {
        selectedRef.current = strokesRef.current.length - 1;
        onToolAutoSwitchRef.current?.("select");
        redraw();
      }

      // Now that no stroke is in progress, it's safe to apply any left-growth
      // that got deferred while this one was being drawn (see maybeGrow).
      if (pendingGrowLeftRef.current > 0 && !growingRef.current) {
        const growLeft = pendingGrowLeftRef.current;
        pendingGrowLeftRef.current = 0;
        applyGrowLeft(growLeft);
      }
    };

    useImperativeHandle(ref, () => ({
      getImageBase64: () => {
        if (imageDataRef.current) return imageDataRef.current.split(",")[1];
        if (!strokesRef.current.length) return null;
        replayStrokesToInk();
        // Exported at the original logical W×H (not W*dpr) — the OCR backend
        // doesn't need Retina-level pixel density, and keeping this size
        // unchanged avoids inflating the upload/vision-API payload. Explicit
        // destination size scales the (now higher-fidelity) ink source down.
        const off = document.createElement("canvas");
        off.width = W;
        off.height = H;
        const octx = off.getContext("2d")!;
        octx.fillStyle = "#ffffff";
        octx.fillRect(0, 0, W, H);
        octx.drawImage(getInkCanvas(), 0, 0, W, H);
        return off.toDataURL("image/png").split(",")[1];
      },
      getInkSnapshot: () => {
        // Same ink layer as getImageBase64(), but with a transparent
        // background instead of getImageBase64()'s opaque white fill (which
        // is right for OCR, but would blot out the ruled paper lines if
        // drawn back as a restore layer via loadBackgroundInk()).
        if (imageDataRef.current || !strokesRef.current.length) return null;
        replayStrokesToInk();
        const off = document.createElement("canvas");
        off.width = W;
        off.height = H;
        off.getContext("2d")!.drawImage(getInkCanvas(), 0, 0, W, H);
        return off.toDataURL("image/png");
      },
      getStrokes: () => {
        if (imageRef.current || !strokesRef.current.length) return null;
        return {
          width: W,
          height: H,
          strokes: cloneStrokes(strokesRef.current),
          redoStack: cloneStrokes(redoStackRef.current),
          grid: gridRef.current ? { ...gridRef.current } : null,
        };
      },
      getStrokesThumb: (maxWidth = 320) => {
        // Small PNG data URL of the ink (white paper) for history cards. Only
        // meaningful for drawn strokes — uploaded images have no ink layer.
        if (imageRef.current || !strokesRef.current.length) return null;
        replayStrokesToInk();
        const tw = Math.min(maxWidth, W);
        const th = Math.max(1, Math.round((H * tw) / W));
        const off = document.createElement("canvas");
        off.width = tw;
        off.height = th;
        const octx = off.getContext("2d")!;
        octx.fillStyle = "#ffffff";
        octx.fillRect(0, 0, tw, th);
        octx.drawImage(getInkCanvas(), 0, 0, tw, th);
        return off.toDataURL("image/png");
      },
      getExportMap: () => {
        // Maps exported-image pixel coords (what the OCR boxes are in) to canvas
        // internal coords. For strokes the export IS the canvas, so scale 1.
        // For loaded images the export is the image, drawn centered + scaled.
        if (imageRef.current) {
          const img = imageRef.current;
          const scale = Math.min((W - 32) / img.width, (H - 32) / img.height);
          return {
            canvasW: W,
            canvasH: H,
            scale,
            offsetX: (W - img.width * scale) / 2,
            offsetY: (H - img.height * scale) / 2,
          };
        }
        return { canvasW: W, canvasH: H, scale: 1, offsetX: 0, offsetY: 0 };
      },
      getLineSnapshots: (boxes) => {
        // Per-line ink snapshots for the line-pop animation. Only meaningful for
        // drawn strokes (loaded images have no ink layer of their own).
        if (imageDataRef.current) return boxes.map(() => null);
        replayStrokesToInk();
        const ink = getInkCanvas();
        const pad = 6;
        // `boxes` are in the app's logical W×H space (same as OCR/getExportMap),
        // but the ink canvas's actual buffer is W*dpr x H*dpr — clamp against
        // the logical W/H, and scale the source rect by dpr when reading pixels
        // back out. The returned x/y/w/h and the snapshot canvas itself stay in
        // logical units (that's the space the SVG overlay positions them in).
        return boxes.map((b) => {
          if (!b || b.length !== 4) return null;
          const sx = Math.max(0, Math.floor(b[0]) - pad);
          const sy = Math.max(0, Math.floor(b[1]) - pad);
          const sw = Math.min(W, Math.ceil(b[2]) + pad) - sx;
          const sh = Math.min(H, Math.ceil(b[3]) + pad) - sy;
          if (sw <= 0 || sh <= 0) return null;
          const c = document.createElement("canvas");
          c.width = sw;
          c.height = sh;
          c.getContext("2d")!.drawImage(ink, sx * dpr, sy * dpr, sw * dpr, sh * dpr, 0, 0, sw, sh);
          return { x: sx, y: sy, w: sw, h: sh, href: c.toDataURL("image/png") };
        });
      },
      hasInk: () => strokesRef.current.length > 0 || !!imageDataRef.current,
      loadImage: (dataUrl: string) => {
        const img = new Image();
        img.onload = () => {
          imageRef.current = img;
          imageDataRef.current = dataUrl;
          strokesRef.current = [];
          redoStackRef.current = [];
          selectedRef.current = null;
          hoverIndexRef.current = null;
          editingRef.current = null;
          redraw();
          onChange?.();
        };
        img.src = dataUrl;
      },
      loadStrokes: (data) => {
        if (!data || !Array.isArray(data.strokes)) return;
        imageRef.current = null;
        imageDataRef.current = null;
        strokesRef.current = data.strokes.map((s) => cloneStrokeDeep(s));
        redoStackRef.current = Array.isArray(data.redoStack) ? data.redoStack.map((s) => cloneStrokeDeep(s)) : [];
        selectedRef.current = null;
        hoverIndexRef.current = null;
        editingRef.current = null;
        gridRef.current = data.grid ? { ...data.grid } : null;
        bgCanvasRef.current = null;
        if (typeof data.width === "number" && data.width > 0) setCanvasWidth(Math.min(MAX_WIDTH, data.width));
        if (typeof data.height === "number" && data.height > 0) setCanvasHeight(Math.min(MAX_HEIGHT, data.height));
        redraw();
        onChange?.();
      },
      loadBackgroundInk: (dataUrl: string) => {
        // Unlike loadImage(), this appends a normal (editable, undoable)
        // stroke rather than switching into the read-only "uploaded photo"
        // mode — used to restore a question's ink when navigating back to it
        // mid-answer, without freezing the canvas against further writing.
        const img = new Image();
        img.onload = () => {
          // naturalWidth/Height, not the enclosing W/H — those reflect
          // whatever THIS canvas instance's size happens to be right now,
          // which won't match the logical size the snapshot was exported at
          // if the page had grown (infinite paper) before it was captured.
          strokesRef.current.push({ kind: "raster", img, w: img.naturalWidth, h: img.naturalHeight });
          redoStackRef.current = [];
          redraw();
          onChange?.();
        };
        img.src = dataUrl;
      },
      clear: () => {
        imageRef.current = null;
        imageDataRef.current = null;
        strokesRef.current = [];
        redoStackRef.current = [];
        selectedRef.current = null;
        hoverIndexRef.current = null;
        editingRef.current = null;
        gridRef.current = null;
        bgCanvasRef.current = null;
        setCanvasWidth(initialW);
        setCanvasHeight(initialH);
        wrapperRef.current?.scrollTo({ top: 0, left: 0 });
        redraw();
        onChange?.();
      },
      setTool: (tool: CanvasTool) => {
        toolRef.current = tool;
        hoverIndexRef.current = null;
        hoverPointRef.current = null;
        editingRef.current = null;
        if (tool !== "select") {
          selectedRef.current = null;
          if (canvasRef.current) canvasRef.current.style.cursor = "";
          redraw();
        }
      },
      setPenWidth: (width: number) => {
        penWidthRef.current = width;
      },
      setEraserWidth: (width: number) => {
        eraserWidthRef.current = width;
      },
      undo: () => {
        if (imageRef.current) {
          imageRef.current = null;
          imageDataRef.current = null;
          redraw();
          onChange?.();
          return;
        }
        const popped = strokesRef.current.pop();
        if (popped) redoStackRef.current.push(popped);
        redraw();
        onChange?.();
      },
      canUndo: () => strokesRef.current.length > 0 || !!imageRef.current,
      redo: () => {
        const restored = redoStackRef.current.pop();
        if (!restored) return;
        strokesRef.current.push(restored);
        redraw();
        onChange?.();
      },
      canRedo: () => redoStackRef.current.length > 0,
      eraseRegion: (box: number[]) => {
        if (box.length !== 4 || imageRef.current) return;
        const [x1, y1, x2, y2] = box;
        redoStackRef.current = [];
        strokesRef.current.push({ kind: "rect", rect: { x1, y1, x2, y2 } });
        redraw();
        onChange?.();
      },
      spawnGrid: (stepX, stepY, origin, scale) => {
        if (!stepX || !stepY || stepX <= 0 || stepY <= 0) return;
        if (imageRef.current) return;
        gridRef.current = {
          ox: origin?.x ?? W / 2,
          oy: origin?.y ?? H / 2,
          stepX,
          stepY,
          scale: scale && scale > 0 ? scale : 40,
        };
        bgCanvasRef.current = null;
        redraw();
        onChange?.();
      },
      setGridSteps: (stepX, stepY) => {
        if (!gridRef.current || !stepX || !stepY || stepX <= 0 || stepY <= 0) return;
        gridRef.current.stepX = stepX;
        gridRef.current.stepY = stepY;
        bgCanvasRef.current = null;
        redraw();
        onChange?.();
      },
      setGridScale: (scale) => {
        if (!gridRef.current || !scale || scale <= 0) return;
        gridRef.current.scale = scale;
        bgCanvasRef.current = null;
        redraw();
        onChange?.();
      },
      moveGrid: (ox, oy) => {
        moveGridTo(ox, oy);
      },
      hideGrid: () => {
        if (!gridRef.current) return;
        gridRef.current = null;
        bgCanvasRef.current = null;
        redraw();
        onChange?.();
      },
      fitGridToWindow: (xMin, xMax, yMin, yMax) => {
        if (imageRef.current) return;
        const ww = xMax - xMin;
        const wh = yMax - yMin;
        if (ww <= 0 || wh <= 0) return;
        const scale = Math.max(10, Math.min(200, Math.min(W / ww, H / wh) * 0.9));
        const ox = W / 2 - ((xMin + xMax) / 2) * scale;
        const oy = H / 2 + ((yMin + yMax) / 2) * scale;
        const prev = gridRef.current;
        gridRef.current = {
          ox,
          oy,
          stepX: prev?.stepX ?? 1,
          stepY: prev?.stepY ?? 1,
          scale,
        };
        bgCanvasRef.current = null;
        redraw();
        onChange?.();
      },
      hasGrid: () => !!gridRef.current,
    }));

    if (fullscreen) {
      return (
        <div
          ref={wrapperRef}
          className="fixed inset-0 overflow-auto bg-[#f2f1ed]"
          style={{ overscrollBehavior: "contain" }}
        >
          <div
            className="relative mt-[92px] mx-8 mb-6 rounded-[3px] overflow-hidden shadow-[0px_2px_10px_0px_rgba(0,0,0,0.07)]"
            style={{ width: W * zoom, height: H * zoom }}
          >
            <canvas
              ref={canvasRef}
              width={W * dpr}
              height={H * dpr}
              style={{ width: W * zoom, height: H * zoom, display: "block" }}
              className={`stylus-surface ${spaceHeld ? "cursor-grab" : "cursor-none"}`}
              onPointerDown={start}
              onPointerMove={move}
              onPointerUp={end}
              onPointerCancel={end}
              onPointerLeave={(e) => {
                hideCursor();
                end(e);
              }}
              onContextMenu={(e) => e.preventDefault()}
            />
            {overlay && (
              <div className="absolute inset-0 z-10 pointer-events-none overflow-visible">
                <svg
                  width={W * zoom}
                  height={H * zoom}
                  viewBox={`0 0 ${W} ${H}`}
                  className="block"
                >
                  {overlay}
                </svg>
              </div>
            )}
          </div>
          <div
            ref={cursorElRef}
            className="fixed z-20 pointer-events-none rounded-full"
            style={{ display: "none", transform: "translate(-50%, -50%)", left: 0, top: 0 }}
          />
        </div>
      );
    }

    return (
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={W * dpr}
          height={H * dpr}
          style={{ aspectRatio: `${W} / ${H}` }}
          className="stylus-surface w-full h-auto border border-slate-200 rounded cursor-none shadow-sm"
          onPointerDown={start}
          onPointerMove={move}
          onPointerUp={end}
          onPointerCancel={end}
          onPointerLeave={(e) => {
            hideCursor();
            end(e);
          }}
          onContextMenu={(e) => e.preventDefault()}
        />
        <div
          ref={cursorElRef}
          className="fixed z-20 pointer-events-none rounded-full"
          style={{ display: "none", transform: "translate(-50%, -50%)", left: 0, top: 0 }}
        />
      </div>
    );
  }
);

Canvas.displayName = "Canvas";

export default Canvas;
