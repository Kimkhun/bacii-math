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
        className="bg-white border border-[#e8e4da] rounded-xl shadow-[0px_4px_16px_0px_rgba(0,0,0,0.1)] px-5 py-[18px] text-sm"
      >
        <div className="text-[#8a857b] text-xs font-medium">I read line {lineNumber} as</div>
        <div className="mt-2.5 text-[15px] text-[#23272e]">
          <MathText text={primary.latex ? `\\(${primary.latex}\\)` : primary.text} />
        </div>
        <div className="mt-3.5 text-[#8a857b] text-xs font-medium">Did you write one of these instead?</div>
        <div className="mt-2.5 space-y-2">
          {candidates.map((c, i) => (
            <button
              key={i}
              onClick={() => onPick(i)}
              className={`group w-full flex items-center justify-between gap-2 rounded-lg px-3.5 py-3 text-left transition-colors ${
                i === 0
                  ? "bg-white border-[1.5px] border-[#b9b2a2] hover:border-[#8a857b]"
                  : "bg-[#faf9f6] border border-[#e8e4da] hover:border-[#b9b2a2]"
              }`}
            >
              <span className="text-[#23272e] text-sm">
                <MathText text={c.latex ? `\\(${c.latex}\\)` : c.text} />
              </span>
              <span className="text-[11px] font-medium text-[#a8a296] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
                Yes, this one
              </span>
            </button>
          ))}
        </div>
        <div className="mt-3.5 flex items-center justify-between">
          <button
            onClick={onWriteAgain}
            className="px-[13px] py-[9px] rounded-[7px] border border-[#dddad1] text-xs font-medium text-[#6b6558] hover:bg-[#faf9f6]"
          >
            Write it again
          </button>
          <button
            onClick={onNone}
            className="px-2 py-1 rounded text-xs font-normal text-[#a8a296] hover:text-[#6b6558]"
          >
            None of these
          </button>
        </div>
      </div>
    </foreignObject>
  );
}
