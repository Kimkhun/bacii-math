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

      {/* curve */}
      {graph.curve.map((seg, i) => (
        <path key={`c${i}`} d={pathOf(seg)} fill="none" stroke="#2563eb" strokeWidth={2.2} strokeLinejoin="round" />
      ))}

      {/* tangent */}
      {graph.tangent && (
        <line
          x1={xTo(graph.tangent[0][0])}
          y1={yTo(graph.tangent[0][1])}
          x2={xTo(graph.tangent[1][0])}
          y2={yTo(graph.tangent[1][1])}
          stroke="#16a34a"
          strokeWidth={2}
        />
      )}

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