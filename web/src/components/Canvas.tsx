"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

export type CanvasTool = "pen" | "eraser";

export interface CanvasHandle {
  getImageBase64: () => string | null;
  hasInk: () => boolean;
  loadImage: (dataUrl: string) => void;
  clear: () => void;
  setTool: (tool: CanvasTool) => void;
}

interface Stroke {
  points: { x: number; y: number }[];
  tool: CanvasTool;
}

const LINE_COLOR = "#c9d7f0";
const MARGIN_COLOR = "#f2b8b8";
const INK_COLOR = "#1f2937";
const LINE_SPACING = 40;
const MARGIN_X = 64;
const FULL_W = 1600;
const FULL_H = 1000;
const ERASER_WIDTH = 32;

const Canvas = forwardRef<CanvasHandle, { width?: number; height?: number; fullscreen?: boolean }>(
  ({ width = 640, height = 820, fullscreen = false }, ref) => {
    const W = fullscreen ? FULL_W : width;
    const H = fullscreen ? FULL_H : height;
    const canvasRef = useRef<HTMLCanvasElement>(null);
    // Ink lives on its own transparent layer so erasing (destination-out) never
    // touches the ruled background drawn underneath it.
    const inkCanvasRef = useRef<HTMLCanvasElement | null>(null);
    const strokesRef = useRef<Stroke[]>([]);
    const imageRef = useRef<HTMLImageElement | null>(null);
    const imageDataRef = useRef<string | null>(null);
    const drawing = useRef(false);
    const toolRef = useRef<CanvasTool>("pen");

    const getInkCanvas = () => {
      if (!inkCanvasRef.current) {
        const c = document.createElement("canvas");
        c.width = W;
        c.height = H;
        inkCanvasRef.current = c;
      }
      return inkCanvasRef.current;
    };

    const strokeStyleFor = (ctx: CanvasRenderingContext2D, tool: CanvasTool) => {
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      if (tool === "eraser") {
        ctx.globalCompositeOperation = "destination-out";
        ctx.lineWidth = ERASER_WIDTH;
      } else {
        ctx.globalCompositeOperation = "source-over";
        ctx.strokeStyle = INK_COLOR;
        ctx.lineWidth = 6;
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
        const points = stroke.points;
        if (points.length < 2) continue;
        strokeStyleFor(ictx, stroke.tool);
        ictx.beginPath();
        ictx.moveTo(points[0].x, points[0].y);
        for (let i = 1; i < points.length; i++) ictx.lineTo(points[i].x, points[i].y);
        ictx.stroke();
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

    useEffect(() => {
      redraw();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const getPos = (e: React.PointerEvent) => {
      const rect = canvasRef.current!.getBoundingClientRect();
      return {
        x: ((e.clientX - rect.left) / rect.width) * W,
        y: ((e.clientY - rect.top) / rect.height) * H,
      };
    };

    const start = (e: React.PointerEvent) => {
      if (imageRef.current) return;
      e.preventDefault();
      drawing.current = true;
      const p = getPos(e);
      strokesRef.current.push({ points: [p], tool: toolRef.current });
      const ictx = getInkCanvas().getContext("2d")!;
      strokeStyleFor(ictx, toolRef.current);
      ictx.beginPath();
      ictx.moveTo(p.x, p.y);
    };

    const move = (e: React.PointerEvent) => {
      if (!drawing.current) return;
      e.preventDefault();
      const p = getPos(e);
      const ictx = getInkCanvas().getContext("2d")!;
      strokeStyleFor(ictx, toolRef.current);
      ictx.lineTo(p.x, p.y);
      ictx.stroke();
      strokesRef.current[strokesRef.current.length - 1].points.push(p);

      const ctx = canvasRef.current!.getContext("2d")!;
      drawRuled(ctx);
      ctx.drawImage(getInkCanvas(), 0, 0);
    };

    const end = () => {
      drawing.current = false;
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
        };
        img.src = dataUrl;
      },
      clear: () => {
        imageRef.current = null;
        imageDataRef.current = null;
        strokesRef.current = [];
        redraw();
      },
      setTool: (tool: CanvasTool) => {
        toolRef.current = tool;
      },
    }));

    return (
      <canvas
        ref={canvasRef}
        width={W}
        height={H}
        style={fullscreen ? undefined : { aspectRatio: `${W} / ${H}` }}
        className={
          fullscreen
            ? "fixed inset-0 w-full h-full cursor-crosshair touch-none"
            : "w-full h-auto border border-slate-200 rounded cursor-crosshair touch-none shadow-sm"
        }
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={end}
        onPointerLeave={end}
      />
    );
  }
);

Canvas.displayName = "Canvas";

export default Canvas;
