"use client";

import MathText from "@/components/MathText";
import { useLanguage } from "@/context/LanguageContext";

import { num } from "./limitPresets";

const S = 200;
const C = S / 2;
const R = 76;

/** Why sin(u)/u -> 1: on the unit circle the arc of angle u has length u and
 * its endpoint sits at height sin u; as u shrinks the two become equal.
 *
 * Like the video, the drawing magnifies around the point (1, 0) as u shrinks
 * (zoom ~ 1/u), so the tiny arc and its height stay big enough to compare. */
export default function UnitCirclePanel({ angle }: { angle: number }) {
  const { t } = useLanguage();
  // Show the angle folded into (-pi, pi] so large k*h still draws sensibly.
  const u = Math.atan2(Math.sin(angle), Math.cos(angle));
  const z = Math.min(150, Math.max(1, 0.6 / Math.max(Math.abs(u), 1e-6)));
  const fx = C + R;
  const fy = C;
  // Unit-circle coordinates -> magnified screen coordinates.
  const at = (x: number, y: number): [number, number] => [fx + z * (C + R * x - fx), fy + z * (C - R * y - fy)];
  const [ox, oy] = at(0, 0);
  const [ax, ay] = at(1, 0);
  const [px, py] = at(Math.cos(u), Math.sin(u));
  const [hx, hy] = at(Math.cos(u), 0);
  const r = R * z;
  const sweep = u > 0 ? 0 : 1;
  const ratio = angle === 0 ? 1 : Math.sin(angle) / angle;

  return (
    <div className="flex flex-col items-center gap-2 rounded-lg bg-slate-50 p-2">
      <svg viewBox={`0 0 ${S} ${S}`} className="invert-in-dark w-full max-w-[220px]" role="img" aria-label="unit circle">
        <defs>
          <clipPath id="unit-circle-clip">
            <rect x={0} y={0} width={S} height={S} />
          </clipPath>
        </defs>
        <g clipPath="url(#unit-circle-clip)">
          <circle cx={ox} cy={oy} r={r} fill="none" stroke="#cbd5e1" strokeWidth={1.2} />
          <line x1={ox - r * 1.2} y1={oy} x2={ox + r * 1.2} y2={oy} stroke="#94a3b8" />
          <line x1={ox} y1={oy} x2={px} y2={py} stroke="#64748b" strokeWidth={1.5} />
          <path d={`M ${ax} ${ay} A ${r} ${r} 0 0 ${sweep} ${px} ${py}`} fill="none" stroke="#f59e0b" strokeWidth={5} strokeLinecap="round" />
          <line x1={px} y1={py} x2={hx} y2={hy} stroke="#14b8a6" strokeWidth={4} />
          <circle cx={px} cy={py} r={3.5} fill="#f59e0b" />
        </g>
        {z > 1.05 && (
          <text x={S - 6} y={S - 6} fontSize={11} textAnchor="end" fill="#94a3b8">
            ×{Math.round(z)}
          </text>
        )}
      </svg>
      <div className="text-center text-xs leading-relaxed text-slate-700 tabular-nums">
        <div>
          <MathText text={`$u = ${num(angle, 4)}, \\ \\sin u = ${num(Math.sin(angle), 4)}$`} />
        </div>
        <div className="font-semibold text-green-700">
          <MathText text={`$\\frac{\\sin u}{u} = ${num(ratio, 4)}$`} />
        </div>
        <div className="mt-1 text-slate-500">
          <MathText text={t("explorer_unit_circle")} />
        </div>
      </div>
    </div>
  );
}
