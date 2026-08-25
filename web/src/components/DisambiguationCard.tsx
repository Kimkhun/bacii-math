"use client";

import MathText from "./MathText";

export interface DisambiguationCandidate {
  text: string;
  latex?: string;
}

const CARD_W = 440;

// Renders inside the practice canvas's SVG overlay via <foreignObject>, so it
// lives in the same canvas-internal coordinate space as the red-pen marks and
// scrolls/zooms with the page. `box` is the ambiguous line's ink box already
// mapped into that coordinate space (same mapping buildMarks/buildWriting use).
export default function DisambiguationCard({
  lineNumber,
  box,
  canvasW,
  primary,
  candidates,
  onPick,
  onNone,
  onWriteAgain,
}: {
  lineNumber: number;
  box: { x1: number; y1: number; x2: number; y2: number };
  canvasW: number;
  primary: DisambiguationCandidate;
  candidates: DisambiguationCandidate[];
  onPick: (index: number) => void;
  onNone: () => void;
  onWriteAgain: () => void;
}) {
  const fitsRight = box.x2 + 24 + CARD_W <= canvasW - 8;
  const x = fitsRight ? box.x2 + 24 : Math.max(8, box.x1 - 24 - CARD_W);
  const y = Math.max(8, box.y1 - 8);
  const height = 140 + candidates.length * 68;

  return (
    <foreignObject x={x} y={y} width={CARD_W} height={height} style={{ overflow: "visible" }}>
      <div
        {...{ xmlns: "http://www.w3.org/1999/xhtml" }}
        style={{ pointerEvents: "auto" }}
        className="bg-white border border-slate-200 rounded-xl shadow-xl p-4 text-sm"
      >
        <div className="text-slate-500">I read line {lineNumber} as</div>
        <div className="mt-1 text-base text-slate-900">
          <MathText text={primary.latex ? `\\(${primary.latex}\\)` : primary.text} />
        </div>
        <div className="mt-3 text-slate-500">Did you write one of these instead?</div>
        <div className="mt-2 space-y-2">
          {candidates.map((c, i) => (
            <button
              key={i}
              onClick={() => onPick(i)}
              className="group w-full flex items-center justify-between gap-2 rounded-lg border border-slate-300 hover:border-emerald-400 hover:bg-emerald-50 px-3 py-2 text-left transition-colors"
            >
              <span className="text-slate-900">
                <MathText text={c.latex ? `\\(${c.latex}\\)` : c.text} />
              </span>
              <span className="text-xs text-emerald-700 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
                Yes, this one
              </span>
            </button>
          ))}
        </div>
        <div className="mt-3 flex items-center justify-between">
          <button
            onClick={onWriteAgain}
            className="px-2 py-1 rounded text-xs font-medium text-slate-700 hover:bg-slate-100"
          >
            Write it again
          </button>
          <button
            onClick={onNone}
            className="px-2 py-1 rounded text-xs font-medium text-slate-400 hover:text-slate-600"
          >
            None of these
          </button>
        </div>
      </div>
    </foreignObject>
  );
}
