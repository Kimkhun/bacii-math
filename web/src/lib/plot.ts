// Shared 2-D plotting helpers for the SVG graphs (FunctionGraph, lesson
// explorers): world -> screen mapping and tick choice. Pure functions, no DOM.

export interface Window2D {
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
}

/** Maps world coordinates into an SVG box of `W x H` with `pad` margins
 * (y grows upward in the world, downward on screen). */
export function makeScale(win: Window2D, W: number, H: number, pad: number) {
  const { x_min, x_max, y_min, y_max } = win;
  const xTo = (x: number) => pad + ((x - x_min) / (x_max - x_min)) * (W - 2 * pad);
  const yTo = (y: number) => H - pad - ((y - y_min) / (y_max - y_min)) * (H - 2 * pad);
  const xFrom = (sx: number) => x_min + ((sx - pad) / (W - 2 * pad)) * (x_max - x_min);
  return { xTo, yTo, xFrom };
}

/** Integer tick step keeping ~6-12 ticks across a window (FunctionGraph's rule). */
export function integerTickStep(win: Window2D): number {
  const range = Math.max(win.x_max - win.x_min, win.y_max - win.y_min);
  return range <= 12 ? 1 : range <= 24 ? 2 : 5;
}

/** A "nice" step (1, 2 or 5 x 10^k) giving about `target` ticks over `span`. */
export function niceStep(span: number, target = 5): number {
  const raw = span / target;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const r = raw / mag;
  return (r < 1.5 ? 1 : r < 3.5 ? 2 : r < 7.5 ? 5 : 10) * mag;
}

/** Multiples of `step` inside [min, max]. */
export function ticks(min: number, max: number, step: number): number[] {
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) {
    out.push(Math.abs(v) < step * 1e-9 ? 0 : v);
  }
  return out;
}

/** Tick label with just enough decimals for `step` (and k/M for big values). */
export function tickLabel(v: number, step: number): string {
  if (Math.abs(v) >= 1e6) return `${+(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e4) return `${+(v / 1e3).toFixed(1)}k`;
  const digits = Math.max(0, -Math.floor(Math.log10(step) + 1e-9));
  return v.toFixed(Math.min(digits, 6));
}
