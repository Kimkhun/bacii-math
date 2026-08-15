"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";

export type CanvasTool = "pen" | "eraser";

export interface CanvasHandle {
  getImageBase64: () => string | null;
  hasInk: () => boolean;
  loadImage: (dataUrl: string) => void;
  clear: () => void;
  setTool: (tool: CanvasTool) => void;
  setPenWidth: (width: number) => void;
  undo: () => void;
  canUndo: () => boolean;
}

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  tool: CanvasTool;
  width: number;
}

const LINE_COLOR = "#c9d7f0";
const MARGIN_COLOR = "#f2b8b8";
const INK_COLOR = "#1f2937";
const LINE_SPACING = 40;
const MARGIN_X = 64;
const FULL_W = 1600;
const FULL_H = 1000;
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
  }
>(({ width = 640, height = 820, fullscreen = false, onChange, zoom = 1, onZoomChange }, ref) => {
    const initialW = fullscreen ? FULL_W : width;
    const initialH = fullscreen ? FULL_H : height;
    const [canvasWidth, setCanvasWidth] = useState(initialW);
    const [canvasHeight, setCanvasHeight] = useState(initialH);
    const W = fullscreen ? canvasWidth : width;
    const H = fullscreen ? canvasHeight : height;
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const wrapperRef = useRef<HTMLDivElement>(null);
    // Ink lives on its own transparent layer so erasing (destination-out) never
    // touches the ruled background drawn underneath it.
    const inkCanvasRef = useRef<HTMLCanvasElement | null>(null);
    const strokesRef = useRef<Stroke[]>([]);
    const imageRef = useRef<HTMLImageElement | null>(null);
    const imageDataRef = useRef<string | null>(null);
    const drawing = useRef(false);
    const toolRef = useRef<CanvasTool>("pen");
    const penWidthRef = useRef<number>(DEFAULT_PEN_WIDTH);

    const getInkCanvas = () => {
      if (!inkCanvasRef.current) {
        const c = document.createElement("canvas");
        c.width = W;
        c.height = H;
        inkCanvasRef.current = c;
      } else if (inkCanvasRef.current.height !== H || inkCanvasRef.current.width !== W) {
        // Resizing clears the buffer; replayStrokesToInk() (called right after,
        // everywhere this matters) repaints it from strokesRef, which is lossless.
        inkCanvasRef.current.width = W;
        inkCanvasRef.current.height = H;
      }
      return inkCanvasRef.current;
    };

    const strokeStyleFor = (ctx: CanvasRenderingContext2D, tool: CanvasTool, width: number) => {
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      if (tool === "eraser") {
        ctx.globalCompositeOperation = "destination-out";
        ctx.lineWidth = ERASER_WIDTH;
      } else {
        ctx.globalCompositeOperation = "source-over";
        ctx.strokeStyle = INK_COLOR;
        ctx.lineWidth = width;
      }
    };

    const drawRuled = (ctx: CanvasRenderingContext2D) => {
      ctx.fillStyle = "#fdfdfd";
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

    const replayStrokesToInk = () => {
      const inkCanvas = getInkCanvas();
      const ictx = inkCanvas.getContext("2d")!;
      ictx.clearRect(0, 0, W, H);
      for (const stroke of strokesRef.current) {
        if (stroke.points.length < 1) continue;
        strokeStyleFor(ictx, stroke.tool, stroke.width);
        drawSmoothPath(ictx, stroke.points);
      }
      ictx.globalCompositeOperation = "source-over";
    };

    const redraw = () => {
      const ctx = canvasRef.current!.getContext("2d")!;
      drawRuled(ctx);
      if (imageRef.current) {
        const img = imageRef.current;
        const scale = Math.min((W - 32) / img.width, (H - 32) / img.height);
        const w = img.width * scale;
        const h = img.height * scale;
        ctx.drawImage(img, (W - w) / 2, (H - h) / 2, w, h);
        return;
      }
      replayStrokesToInk();
      ctx.drawImage(getInkCanvas(), 0, 0);
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
    useEffect(() => {
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
        for (const p of s.points) p.x += dx;
      }
    };

    const getPos = (e: React.PointerEvent) => {
      const rect = canvasRef.current!.getBoundingClientRect();
      return {
        x: ((e.clientX - rect.left) / rect.width) * W,
        y: ((e.clientY - rect.top) / rect.height) * H,
      };
    };

    const maybeGrow = (p: Point) => {
      if (!fullscreen || growingRef.current) return;

      const growH = H - p.y <= GROW_THRESHOLD && H < MAX_HEIGHT ? Math.min(GROW_CHUNK, MAX_HEIGHT - H) : 0;
      const growRight = W - p.x <= GROW_THRESHOLD && W < MAX_WIDTH ? Math.min(GROW_CHUNK, MAX_WIDTH - W) : 0;
      const growLeft = !growRight && p.x <= GROW_THRESHOLD && W < MAX_WIDTH ? Math.min(GROW_CHUNK, MAX_WIDTH - W) : 0;

      if (!growH && !growRight && !growLeft) return;
      growingRef.current = true;

      if (growLeft) shiftStrokesX(growLeft);
      grownRef.current = { top: growH, left: growRight + growLeft };

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
      // Palm rejection: while a stylus is actively writing, ignore stray touch
      // contacts (a resting palm) entirely rather than starting a stroke/pan with them.
      if (e.pointerType === "touch" && activePenPointerRef.current !== null) return;

      if (e.pointerType === "touch") {
        (e.target as Element).setPointerCapture?.(e.pointerId);
        touchPointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (touchPointersRef.current.size === 2) {
          // Second finger down: cancel any single-finger stroke just begun and
          // switch to two-finger pan + pinch-zoom, the touch equivalent of
          // desktop's "hold Space to pan" / scroll-wheel zoom.
          if (drawing.current) {
            strokesRef.current.pop();
            drawing.current = false;
            redraw();
          }
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
      const p = getPos(e);
      const width = toolRef.current === "pen" ? penWidthRef.current : ERASER_WIDTH;
      strokesRef.current.push({ points: [p], tool: toolRef.current, width });
      redraw();
      maybeGrow(p);
    };

    const move = (e: React.PointerEvent) => {
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
      if (!drawing.current) return;
      e.preventDefault();
      const p = getPos(e);
      strokesRef.current[strokesRef.current.length - 1].points.push(p);
      redraw();
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
      if (!drawing.current) return;
      drawing.current = false;
      onChange?.();
    };

    useImperativeHandle(ref, () => ({
      getImageBase64: () => {
        if (imageDataRef.current) return imageDataRef.current.split(",")[1];
        if (!strokesRef.current.length) return null;
        replayStrokesToInk();
        const off = document.createElement("canvas");
        off.width = W;
        off.height = H;
        const octx = off.getContext("2d")!;
        octx.fillStyle = "#ffffff";
        octx.fillRect(0, 0, W, H);
        octx.drawImage(getInkCanvas(), 0, 0);
        return off.toDataURL("image/png").split(",")[1];
      },
      hasInk: () => strokesRef.current.length > 0 || !!imageDataRef.current,
      loadImage: (dataUrl: string) => {
        const img = new Image();
        img.onload = () => {
          imageRef.current = img;
          imageDataRef.current = dataUrl;
          strokesRef.current = [];
          redraw();
          onChange?.();
        };
        img.src = dataUrl;
      },
      clear: () => {
        imageRef.current = null;
        imageDataRef.current = null;
        strokesRef.current = [];
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
      undo: () => {
        if (imageRef.current) {
          imageRef.current = null;
          imageDataRef.current = null;
          redraw();
          onChange?.();
          return;
        }
        strokesRef.current.pop();
        redraw();
        onChange?.();
      },
      canUndo: () => strokesRef.current.length > 0 || !!imageRef.current,
    }));

    if (fullscreen) {
      return (
        <div ref={wrapperRef} className="fixed inset-0 overflow-auto bg-slate-200">
          <canvas
            ref={canvasRef}
            width={W}
            height={H}
            style={{ width: W * zoom, height: H * zoom, display: "block" }}
            className={`touch-none m-6 shadow-md ${spaceHeld ? "cursor-grab" : "cursor-crosshair"}`}
            onPointerDown={start}
            onPointerMove={move}
            onPointerUp={end}
            onPointerCancel={end}
            onPointerLeave={end}
          />
        </div>
      );
    }

    return (
      <canvas
        ref={canvasRef}
        width={W}
        height={H}
        style={{ aspectRatio: `${W} / ${H}` }}
        className="w-full h-auto border border-slate-200 rounded cursor-crosshair touch-none shadow-sm"
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={end}
        onPointerCancel={end}
        onPointerLeave={end}
      />
    );
  }
);

Canvas.displayName = "Canvas";

export default Canvas;
