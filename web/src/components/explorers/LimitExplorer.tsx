"use client";

import { useEffect, useRef, useState } from "react";

import MathText from "@/components/MathText";
import { useLanguage } from "@/context/LanguageContext";
import { Window2D, makeScale, niceStep, tickLabel, ticks } from "@/lib/plot";

import { LIMIT_PRESETS, LimitPreset, Params, num } from "./limitPresets";
import UnitCirclePanel from "./UnitCirclePanel";

const PAD = 26;
const SAMPLES = 320;
/** The approach slider spans h = hMax down to hMax * 10^-DECADES. */
const DECADES = 4;
/** x -> +infinity: the slider runs x from X_START out to X_END (log scale). */
const X_START = 1;
const X_END = 1e6;
const STEPS = 1000;

const COLORS = {
  curve: "#0284c7", // sky-600
  overlay: "#10b981", // emerald-500
  rider: "#f59e0b", // amber-500
  limit: "#16a34a", // green-600
  axis: "#475569", // slate-600
  grid: "#e2e8f0", // slate-200
};

function defaults(preset: LimitPreset): Params {
  return Object.fromEntries(preset.params.map((s) => [s.key, s.value]));
}

/** Polyline segments of f over the window, broken wherever f is undefined or
 * leaves the window by a wide margin (so asymptotes don't draw a wall). */
function sample(f: (x: number) => number, win: Window2D): [number, number][][] {
  const span = win.y_max - win.y_min;
  const lo = win.y_min - 2 * span;
  const hi = win.y_max + 2 * span;
  const segs: [number, number][][] = [];
  let cur: [number, number][] = [];
  for (let i = 0; i <= SAMPLES; i++) {
    const x = win.x_min + ((win.x_max - win.x_min) * i) / SAMPLES;
    const y = f(x);
    if (Number.isFinite(y) && y > lo && y < hi) cur.push([x, y]);
    else if (cur.length) {
      segs.push(cur);
      cur = [];
    }
  }
  if (cur.length) segs.push(cur);
  return segs;
}

/**
 * Interactive "Explore" mode for a limit lesson. Students drag across the
 * graph (or use the slider) to bring x toward the point — or out toward
 * +infinity — and watch f(x) close in on the limit; parameter sliders turn
 * the lesson's example into a whole family.
 *
 * Purely event-driven: it re-renders on input and never runs an animation
 * loop, so it costs nothing while idle.
 */
export default function LimitExplorer({ presetId }: { presetId: string }) {
  const preset = LIMIT_PRESETS[presetId];
  const { t } = useLanguage();
  const [params, setParams] = useState<Params>(() => defaults(preset));
  const [step, setStep] = useState(STEPS * 0.15);
  const [zoom, setZoom] = useState(false);
  const [overlay, setOverlay] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);
  const dragging = useRef(false);
  // The SVG's coordinate system is its real size in CSS pixels, so tick
  // labels stay legible on a phone instead of shrinking with the graph.
  const [{ W, H }, setSize] = useState({ W: 560, H: 320 });
  useEffect(() => {
    const el = svgRef.current?.parentElement;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const w = Math.max(240, Math.round(svgRef.current?.clientWidth ?? el.clientWidth));
      setSize({ W: w, H: Math.round(Math.min(340, Math.max(210, w * 0.62))) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const target = preset.target(params);
  const atInfinity = target === "inf";
  const a = atInfinity ? 0 : target;
  const both = !atInfinity && preset.side !== "right";
  const lim = preset.limit(params);
  const f = (x: number) => preset.f(x, params);
  const hMax = preset.hMax ?? 2;

  // Slider position -> distance h from a (finite) or x itself (infinity).
  const h = hMax * Math.pow(10, (-DECADES * step) / STEPS);
  const xFar = X_START * Math.pow(X_END / X_START, step / STEPS);

  const base = preset.window(params);
  const win = viewWindow();

  function viewWindow(): Window2D {
    if (atInfinity) {
      // Zoom out as x runs away, so the curve visibly hugs its asymptote.
      return { ...base, x_max: Math.max(base.x_max, xFar * 1.15) };
    }
    if (zoom && Number.isFinite(lim.value)) {
      // Follow the riders in: keep both on screen and the slope looking the same.
      const xHalf = Math.max(h * 2.5, 1e-5);
      const yHalf = (xHalf * (base.y_max - base.y_min)) / (base.x_max - base.x_min);
      return { x_min: a - xHalf, x_max: a + xHalf, y_min: lim.value - yHalf, y_max: lim.value + yHalf };
    }
    return base;
  }

  const { xTo, yTo, xFrom } = makeScale(win, W, H, PAD);
  const curve = sample(f, win);
  const extra = overlay && preset.overlay ? sample((x) => preset.overlay!.f(x, params), win) : [];
  const path = (pts: [number, number][]) =>
    pts.map((p, i) => `${i ? "L" : "M"}${xTo(p[0]).toFixed(1)} ${yTo(p[1]).toFixed(1)}`).join(" ");

  const xs = ticks(win.x_min, win.x_max, niceStep(win.x_max - win.x_min));
  const ys = ticks(win.y_min, win.y_max, niceStep(win.y_max - win.y_min, 4));
  const xStep = niceStep(win.x_max - win.x_min);
  const yStep = niceStep(win.y_max - win.y_min, 4);
  const axisY = Math.min(Math.max(0, win.y_min), win.y_max);
  const axisX = Math.min(Math.max(0, win.x_min), win.x_max);

  const riders = atInfinity ? [xFar] : both ? [a - h, a + h] : [a + h];
  const finiteL = Number.isFinite(lim.value);
  const inWin = (x: number, y: number) =>
    x >= win.x_min && x <= win.x_max && y >= win.y_min && y <= win.y_max;

  // Drag on the graph: horizontal position sets how close x is.
  const fromPointer = (e: React.PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const ctm = svg.getScreenCTM();
    if (!ctm) return;
    // Client -> SVG user space (accounts for the letterboxing of max-h).
    const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
    const x = xFrom(pt.x);
    if (atInfinity) {
      const clamped = Math.min(Math.max(x, X_START), X_END);
      setStep(Math.round((STEPS * Math.log(clamped / X_START)) / Math.log(X_END / X_START)));
    } else {
      const d = Math.min(Math.max(Math.abs(x - a), hMax * Math.pow(10, -DECADES)), hMax);
      setStep(Math.round((STEPS * -Math.log10(d / hMax)) / DECADES));
    }
  };

  const reset = () => {
    setParams(defaults(preset));
    setStep(STEPS * 0.15);
    setZoom(false);
    setOverlay(false);
  };

  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-3 sm:p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="overflow-x-auto text-slate-900">
          <MathText text={`$\\displaystyle ${preset.expression(params)} = ${lim.latex}$`} />
        </div>
        <button onClick={reset} className="text-xs font-medium text-slate-500 hover:text-slate-800">
          {t("explorer_reset")}
        </button>
      </div>

      <div className={preset.extra ? "grid gap-3 sm:grid-cols-[3fr_2fr]" : ""}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          className="invert-in-dark w-full touch-none select-none rounded-lg bg-slate-50"
          role="img"
          aria-label={t("explorer_hint")}
          onPointerDown={(e) => {
            dragging.current = true;
            e.currentTarget.setPointerCapture(e.pointerId);
            fromPointer(e);
          }}
          onPointerMove={(e) => dragging.current && fromPointer(e)}
          onPointerUp={() => (dragging.current = false)}
          onPointerCancel={() => (dragging.current = false)}
        >
          <defs>
            <clipPath id={`clip-${presetId}`}>
              <rect x={PAD} y={PAD} width={W - 2 * PAD} height={H - 2 * PAD} />
            </clipPath>
          </defs>
          {xs.map((v) => (
            <line key={`gx${v}`} x1={xTo(v)} y1={PAD} x2={xTo(v)} y2={H - PAD} stroke={COLORS.grid} />
          ))}
          {ys.map((v) => (
            <line key={`gy${v}`} x1={PAD} y1={yTo(v)} x2={W - PAD} y2={yTo(v)} stroke={COLORS.grid} />
          ))}
          <line x1={PAD} y1={yTo(axisY)} x2={W - PAD} y2={yTo(axisY)} stroke={COLORS.axis} strokeWidth={1.4} />
          <line x1={xTo(axisX)} y1={PAD} x2={xTo(axisX)} y2={H - PAD} stroke={COLORS.axis} strokeWidth={1.2} />
          {xs.filter((v) => v !== axisX).map((v) => (
            <text key={`tx${v}`} x={xTo(v)} y={Math.min(yTo(axisY) + 14, H - 6)} fontSize={11} textAnchor="middle" fill="#64748b">
              {tickLabel(v, xStep)}
            </text>
          ))}
          {ys.filter((v) => v !== axisY).map((v) => (
            <text key={`ty${v}`} x={PAD + 4} y={yTo(v) - 4} fontSize={11} textAnchor="start" fill="#64748b">
              {tickLabel(v, yStep)}
            </text>
          ))}

          <g clipPath={`url(#clip-${presetId})`}>
            {finiteL && (
              <line
                x1={PAD}
                x2={W - PAD}
                y1={yTo(lim.value)}
                y2={yTo(lim.value)}
                stroke={COLORS.limit}
                strokeWidth={1.2}
                strokeDasharray="5 4"
              />
            )}
            {extra.map((seg, i) => (
              <path key={`o${i}`} d={path(seg)} fill="none" stroke={COLORS.overlay} strokeWidth={4} opacity={0.45} />
            ))}
            {curve.map((seg, i) => (
              <path key={`c${i}`} d={path(seg)} fill="none" stroke={COLORS.curve} strokeWidth={2.2} strokeLinejoin="round" />
            ))}
            {!atInfinity && finiteL && (
              <circle
                cx={xTo(a)}
                cy={yTo(lim.value)}
                r={4.5}
                fill={preset.continuous ? COLORS.limit : "#f8fafc"}
                stroke={preset.continuous ? COLORS.limit : COLORS.curve}
                strokeWidth={2}
              />
            )}
            {riders.map((x, i) => {
              const y = f(x);
              if (!Number.isFinite(y)) return null;
              const cx = inWin(x, y) ? xTo(x) : xTo(Math.min(Math.max(x, win.x_min), win.x_max));
              const cy = yTo(Math.min(Math.max(y, win.y_min), win.y_max));
              return (
                <g key={i}>
                  <line x1={cx} y1={yTo(axisY)} x2={cx} y2={cy} stroke={COLORS.rider} strokeWidth={1} strokeDasharray="2 3" />
                  <circle cx={cx} cy={cy} r={5} fill={COLORS.rider} stroke="white" strokeWidth={1.5} />
                </g>
              );
            })}
          </g>
        </svg>

        {preset.extra === "unit-circle" && <UnitCirclePanel angle={params.k * h} />}
      </div>

      <ValueTable
        riders={riders}
        f={f}
        limit={lim.value}
        atInfinity={atInfinity}
        labels={both ? [t("explorer_left"), t("explorer_right")] : [atInfinity ? "x → +∞" : t("explorer_right")]}
        gapLabel={t("explorer_gap")}
      />

      <div className="space-y-3">
        <Slider
          label={atInfinity ? t("explorer_x_far") : t("explorer_distance")}
          value={step}
          min={0}
          max={STEPS}
          step={1}
          onChange={setStep}
          readout={atInfinity ? `x = ${num(xFar, 0)}` : `h = ${num(h, 5)}`}
        />
        {preset.params.map((s) => (
          <Slider
            key={s.key}
            label={`$${s.label}$`}
            value={params[s.key]}
            min={s.min}
            max={s.max}
            step={s.step}
            onChange={(v) => setParams((p) => ({ ...p, [s.key]: v }))}
            readout={num(params[s.key], 2)}
          />
        ))}
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-700">
          {!atInfinity && (
            <Toggle checked={zoom} onChange={setZoom} label={t("explorer_zoom")} />
          )}
          {preset.overlay && (
            <Toggle checked={overlay} onChange={setOverlay} label={t(preset.overlay.label)} />
          )}
        </div>
        <p className="text-xs text-slate-500">{t("explorer_hint")}</p>
      </div>
    </div>
  );
}

function ValueTable({
  riders,
  f,
  limit,
  atInfinity,
  labels,
  gapLabel,
}: {
  riders: number[];
  f: (x: number) => number;
  limit: number;
  atInfinity: boolean;
  labels: string[];
  gapLabel: string;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {riders.map((x, i) => {
        const y = f(x);
        const gap = Number.isFinite(limit) ? Math.abs(y - limit) : NaN;
        return (
          <div key={i} className="rounded-lg bg-amber-50 px-3 py-2 text-sm tabular-nums">
            <div className="text-xs font-semibold text-amber-700">{labels[i]}</div>
            <div className="text-slate-800">
              x = {num(x, atInfinity ? 0 : 6)} &nbsp;→&nbsp; f(x) = {Number.isFinite(y) ? num(y, 6) : "—"}
            </div>
            {Number.isFinite(gap) && (
              <div className="text-xs text-slate-500">
                {gapLabel}: {gap < 1e-6 ? gap.toExponential(1) : num(gap, 6)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  onChange,
  readout,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  readout: string;
}) {
  return (
    <label className="grid grid-cols-[minmax(4.5rem,auto)_1fr_5.5rem] items-center gap-3 text-sm text-slate-700">
      <span className="text-xs font-medium text-slate-600">
        <MathText text={label} />
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-sky-500 stylus:h-8"
      />
      <span className="text-right font-mono text-xs tabular-nums text-slate-600">{readout}</span>
    </label>
  );
}

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="flex cursor-pointer items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 accent-sky-500 stylus:h-6 stylus:w-6"
      />
      {label}
    </label>
  );
}
