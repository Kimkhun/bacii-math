"use client";

import { GraphSpec } from "@/lib/api";

// Renders the SymPy-sampled reference graph as pure SVG: axes + ticks, the
// curve (one path per segment so asymptote gaps stay clean), dashed vertical
// asymptotes, the tangent line, and labeled points (e.g. the origin). The
// backend sends sampled points — no math is evaluated in the browser.
export default function FunctionGraph({ graph }: { graph: GraphSpec }) {
  const pad = 26;
  const W = 340;
  const H = 240;
  const { x_min, x_max, y_min, y_max } = graph;
  const xTo = (x: number) => pad + ((x - x_min) / (x_max - x_min)) * (W - 2 * pad);
  const yTo = (y: number) => H - pad - ((y - y_min) / (y_max - y_min)) * (H - 2 * pad);

  const axisX = yTo(0);
  const axisY = xTo(0);
  const inX = (v: number) => v >= x_min && v <= x_max;
  const inY = (v: number) => v >= y_min && v <= y_max;

  const pathOf = (pts: number[][]) =>
    pts
      .map((p, i) => `${i === 0 ? "M" : "L"}${xTo(p[0]).toFixed(1)} ${yTo(p[1]).toFixed(1)}`)
      .join(" ");

  // Integer tick grid: choose a step that keeps ~6-12 ticks across the window.
  const range = Math.max(x_max - x_min, y_max - y_min);
  const step = range <= 12 ? 1 : range <= 24 ? 2 : 5;
  const xTicks: number[] = [];
  const yTicks: number[] = [];
  for (let v = Math.ceil(x_min / step) * step; v <= x_max; v += step) xTicks.push(v);
  for (let v = Math.ceil(y_min / step) * step; v <= y_max; v += step) yTicks.push(v);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full h-auto bg-white"
      role="img"
      aria-label="Reference graph of the function"
    >
      {/* grid */}
      {xTicks.map((v) => (
        <line key={`gx${v}`} x1={xTo(v)} y1={pad} x2={xTo(v)} y2={H - pad} stroke="#eef2f7" strokeWidth={1} />
      ))}
      {yTicks.map((v) => (
        <line key={`gy${v}`} x1={pad} y1={yTo(v)} x2={W - pad} y2={yTo(v)} stroke="#eef2f7" strokeWidth={1} />
      ))}

      {/* axes */}
      <line x1={pad} y1={axisY} x2={W - pad} y2={axisY} stroke="#334155" strokeWidth={1.5} />
      <line x1={axisX} y1={pad} x2={axisX} y2={H - pad} stroke="#334155" strokeWidth={1.5} />
      <text x={W - pad + 4} y={axisY + 4} fontSize={12} fill="#334155" fontWeight={700}>x</text>
      <text x={axisX - 4} y={pad - 5} fontSize={12} fill="#334155" fontWeight={700}>y</text>
      {xTicks.filter((v) => v !== 0 && inX(v)).map((v) => (
        <text key={`tx${v}`} x={xTo(v)} y={axisY + 13} fontSize={9} textAnchor="middle" fill="#64748b">
          {v}
        </text>
      ))}
      {yTicks.filter((v) => v !== 0 && inY(v)).map((v) => (
        <text key={`ty${v}`} x={axisX - 5} y={yTo(v) + 3} fontSize={9} textAnchor="end" fill="#64748b">
          {v}
        </text>
      ))}
      <text x={axisX - 5} y={axisY + 13} fontSize={9} textAnchor="end" fill="#64748b">0</text>

      {/* vertical asymptotes */}
      {graph.vertical_asymptotes.filter((v) => inX(v)).map((v) => (
        <line key={`a${v}`} x1={xTo(v)} y1={pad} x2={xTo(v)} y2={H - pad} stroke="#dc2626" strokeWidth={1.5} strokeDasharray="6 4" />
      ))}

      {/* oblique / horizontal asymptote lines */}
      {(graph.asymptote_lines ?? []).map((al, i) => {
        const [p1, p2] = al.points ?? [];
        if (!p1 || !p2) return null;
        const inRange = (p: number[]) => inX(p[0]) && inY(p[1]);
        const len = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
        if (!len) return null;
        const ux = (p2[0] - p1[0]) / len;
        const uy = (p2[1] - p1[1]) / len;
        const extend = 0.15 * (x_max - x_min) / Math.max(Math.abs(ux), 1e-6);
        const q1 = [p1[0] - ux * extend, p1[1] - uy * extend];
        const q2 = [p2[0] + ux * extend, p2[1] + uy * extend];
        if (!inRange(q1) && !inRange(q2)) return null;
        const c1 = inRange(q1) ? q1 : q2;
        const c2 = inRange(q1) ? q2 : q1;
        return (
          <g key={`al${i}`}>
            <line
              x1={xTo(c1[0])} y1={yTo(c1[1])}
              x2={xTo(c2[0])} y2={yTo(c2[1])}
              stroke="#dc2626" strokeWidth={1.3} strokeDasharray="8 4"
            />
            {al.label && inX((c1[0] + c2[0]) / 2) && (
              <text x={xTo((c1[0] + c2[0]) / 2) + 4} y={yTo((c1[1] + c2[1]) / 2) - 6} fontSize={10} fill="#dc2626">
                {al.label}
              </text>
            )}
          </g>
        );
      })}

      {/* curve */}
      {graph.curve.map((seg, i) => (
        <path key={`c${i}`} d={pathOf(seg)} fill="none" stroke="#2563eb" strokeWidth={2.2} strokeLinejoin="round" />
      ))}

      {/* tangent(s) */}
      {(graph.tangents?.length ? graph.tangents : graph.tangent ? [graph.tangent] : []).map((tangent, i) => (
        <line
          key={`t${i}`}
          x1={xTo(tangent[0][0])}
          y1={yTo(tangent[0][1])}
          x2={xTo(tangent[1][0])}
          y2={yTo(tangent[1][1])}
          stroke="#16a34a"
          strokeWidth={2}
        />
      ))}

      {/* labeled points */}
      {graph.points.filter((p) => inX(p.x) && inY(p.y)).map((p, i) => (
        <g key={`p${i}`}>
          <circle cx={xTo(p.x)} cy={yTo(p.y)} r={3.2} fill="#334155" />
          {p.label && (
            <text x={xTo(p.x) + 6} y={yTo(p.y) - 6} fontSize={11} fill="#334155" fontWeight={700}>
              {p.label}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}