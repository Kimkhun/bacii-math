"use client";

import { forwardRef, ReactNode, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState } from "react";

export type CanvasTool = "pen" | "eraser";

export interface CanvasExportMap {
  canvasW: number;
  canvasH: number;
  scale: number;
  offsetX: number;
  offsetY: number;
}

export interface CanvasHandle {
  getImageBase64: () => string | null;
  getExportMap: () => CanvasExportMap;
  getLineSnapshots: (boxes: (number[] | null)[]) => (LineSnapshot | null)[];
  hasInk: () => boolean;
  loadImage: (dataUrl: string) => void;
  clear: () => void;
  setTool: (tool: CanvasTool) => void;
  setPenWidth: (width: number) => void;
  setEraserWidth: (width: number) => void;
  undo: () => void;
  canUndo: () => boolean;
  redo: () => void;
  canRedo: () => boolean;
  eraseRegion: (box: number[]) => void;
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

// A rectangular region erase (used by "write it again" on a mis-read line) —
// modeled as its own stroke kind so it survives replayStrokesToInk() (canvas
// resizes) and participates in undo/redo like any other stroke.
interface RectStroke {
  kind: "rect";
  rect: { x1: number; y1: number; x2: number; y2: number };
}

type Stroke = PathStroke | RectStroke;

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
  }
>(({ width = 640, height = 820, fullscreen = false, onChange, zoom = 1, onZoomChange, overlay }, ref) => {
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
    const dpr = typeof window !== "undefined" ? Math.min(window.devicePixelRatio || 1, 3) : 1;
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
    const cursorElRef = useRef<HTMLDivElement>(null);

    const updateCursor = (clientX: number, clientY: number) => {
      const el = cursorElRef.current;
      if (!el) return;
      const isPen = toolRef.current === "pen";
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
      if (!inkCanvasRef.current) {
        const c = document.createElement("canvas");
        c.width = W * dpr;
        c.height = H * dpr;
        inkCanvasRef.current = c;
      } else if (inkCanvasRef.current.height !== H * dpr || inkCanvasRef.current.width !== W * dpr) {
        // Resizing clears the buffer; replayStrokesToInk() (called right after,
        // everywhere this matters) repaints it from strokesRef, which is lossless.
        inkCanvasRef.current.width = W * dpr;
        inkCanvasRef.current.height = H * dpr;
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

    // The ruled background is static per canvas size, so render it once into its
    // own layer and composite it — redrawing ~300 lines on every pointer move is
    // what made the cursor lag once the canvas had grown.
    const getBgCanvas = () => {
      if (!bgCanvasRef.current || bgCanvasRef.current.width !== W * dpr || bgCanvasRef.current.height !== H * dpr) {
        const c = document.createElement("canvas");
        c.width = W * dpr;
        c.height = H * dpr;
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
        drawStroke(ictx, stroke);
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
        return tag === "INPUT" || tag === "TEXTAREA";
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
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("keyup", onKeyUp);
      return () => {
        window.removeEventListener("keydown", onKeyDown);
        window.removeEventListener("keyup", onKeyUp);
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
      if (g.top || g.left) {
        wrapperRef.current?.scrollBy({ top: g.top * zoom, left: g.left * zoom });
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
        } else {
          for (const p of s.points) p.x += dx;
        }
      }
      for (const s of redoStackRef.current) {
        if (s.kind === "rect") {
          s.rect.x1 += dx;
          s.rect.x2 += dx;
        } else {
          for (const p of s.points) p.x += dx;
        }
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

    const start = (e: React.PointerEvent) => {
      updateCursor(e.clientX, e.clientY);

      if (e.pointerType === "touch") {
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
      const p = getPos(e.clientX, e.clientY, e.pressure);
      const width = toolRef.current === "pen" ? penWidthRef.current : eraserWidthRef.current;
      redoStackRef.current = [];
      strokesRef.current.push({
        kind: "path",
        points: [p],
        tool: toolRef.current,
        width,
        pointerType: e.pointerType,
      });
      redraw();
      maybeGrow(p);
    };

    const move = (e: React.PointerEvent) => {
      updateCursor(e.clientX, e.clientY);
      if (e.pointerType === "touch" && touchPointersRef.current.has(e.pointerId)) {
        touchPointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
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
      if (stroke.kind === "path") {
        for (const ev of events) {
          p = getPos(ev.clientX, ev.clientY, ev.pressure);
          stroke.points.push(p);
        }
      }
      requestRedraw();
      maybeGrow(p);
    };

    const end = (e: React.PointerEvent) => {
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
        setCanvasWidth(initialW);
        setCanvasHeight(initialH);
        wrapperRef.current?.scrollTo({ top: 0, left: 0 });
        redraw();
        onChange?.();
      },
      setTool: (tool: CanvasTool) => {
        toolRef.current = tool;
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
    }));

    if (fullscreen) {
      return (
        <div ref={wrapperRef} className="fixed inset-0 overflow-auto bg-[#f2f1ed]">
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
