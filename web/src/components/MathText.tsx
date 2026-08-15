"use client";

import renderMathInElement from "katex/contrib/auto-render";
import "katex/dist/katex.min.css";
import { useEffect, useRef } from "react";

const DELIMITERS = [
  { left: "\\[", right: "\\]", display: true },
  { left: "$$", right: "$$", display: true },
  { left: "\\(", right: "\\)", display: false },
];

// Renders plain text that may contain inline/display LaTeX math delimited by
// \( \), \[ \], or $$ $$ (what both our backend step text and the LLM's
// work-check responses use) — everything else stays as ordinary text.
export default function MathText({ text, className }: { text: string; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    try {
      renderMathInElement(ref.current, { delimiters: DELIMITERS, throwOnError: false });
    } catch {
      /* leave as plain text on failure */
    }
  }, [text]);

  return (
    <div ref={ref} className={className}>
      {text}
    </div>
  );
}
