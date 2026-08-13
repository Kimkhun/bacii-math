"use client";

import { forwardRef, useImperativeHandle, useRef } from "react";

export interface CanvasHandle {
  getImageBase64: () => string | null;
  hasInk: () => boolean;
  clear: () => void;
}

const Canvas = forwardRef<CanvasHandle, { width?: number; height?: number }>(
  ({ width = 640, height = 360 }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const drawing = useRef(false);
    const last = useRef({ x: 0, y: 0 });
    const hasInkRef = useRef(false);

    const getPos = (e: React.PointerEvent) => {
      const rect = canvasRef.current!.getBoundingClientRect();
      return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };

    const start = (e: React.PointerEvent) => {
      e.preventDefault();
      drawing.current = true;
      const p = getPos(e);
      last.current = p;
      const ctx = canvasRef.current!.getContext("2d")!;
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
    };

    const move = (e: React.PointerEvent) => {
      if (!drawing.current) return;
      e.preventDefault();
      const p = getPos(e);
      const ctx = canvasRef.current!.getContext("2d")!;
      ctx.lineWidth = 6;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.strokeStyle = "#000";
      ctx.lineTo(p.x, p.y);
      ctx.stroke();
      last.current = p;
      hasInkRef.current = true;
    };

    const end = () => {
      drawing.current = false;
    };

    useImperativeHandle(ref, () => ({
      getImageBase64: () => {
        if (!hasInkRef.current) return null;
        return canvasRef.current!.toDataURL("image/png").split(",")[1];
      },
      hasInk: () => hasInkRef.current,
      clear: () => {
        const c = canvasRef.current!;
        const ctx = c.getContext("2d")!;
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, 0, c.width, c.height);
        hasInkRef.current = false;
      },
    }));

    return (
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="w-full h-auto border border-slate-300 rounded bg-white cursor-crosshair touch-none"
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
