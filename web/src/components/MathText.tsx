"use client";

import renderMathInElement from "katex/contrib/auto-render";
import "katex/dist/katex.min.css";
import { useEffect, useRef } from "react";

const DELIMITERS = [
  { left: "\\[", right: "\\]", display: true },
  { left: "$$", right: "$$", display: true },
  { left: "\\(", right: "\\)", display: false },
  { left: "$", right: "$", display: false },
];

function sanitizeMathText(text: string): string {
  if (!text) return "";
  // If the text contains bare LaTeX commands (e.g. \lim, \frac, \sqrt) not wrapped in $ or \(
  // we auto-wrap them or normalize.
  let s = text.replace(/\\\(|\\\)/g, "$");
  // If the entire text or a subsegment has \lim_{...} or \frac{...} without any $, wrap it
  if (!s.includes("$") && !s.includes("\\[") && /\\(lim|frac|int|sqrt|log|ln|infty|to|pm|times|div|cdot|approx|neq|le|ge|[a-zA-Z]+)\b/.test(s)) {
    // Check if it's a mixed sentence like "ដូចនេះ \lim_{...} = \infty"
    // Wrap LaTeX math parts in $...$
    s = s.replace(/((?:\\[a-zA-Z]+(?:\{[^{}]*\}|\[[^[\]]*\]|_\{[^{}]*\}|\^[^{}]*\}|_[a-zA-Z0-9\+\-]+|\^[a-zA-Z0-9\+\-]+|[ \t]*=[ \t]*|[ \t]*\+[ \t]*|[ \t]*\-[ \t]*|[ \t]*\*[ \t]*|[ \t]*\/[ \t]*|[a-zA-Z0-9\(\)\+\-\*\/\,\. ])*)+)/g, (match) => {
      const trimmed = match.trim();
      if (/\\(lim|frac|int|sqrt|log|ln|infty|to|pm|times|div|cdot|approx|neq|le|ge)/.test(trimmed)) {
        return ` $${trimmed}$ `;
      }
      return match;
    });
  }
  return s;
}

if (typeof window !== "undefined" && !(window as unknown as { __katex_warn_filtered?: boolean }).__katex_warn_filtered) {
  (window as unknown as { __katex_warn_filtered?: boolean }).__katex_warn_filtered = true;
  const originalWarn = console.warn;
  console.warn = (...args: unknown[]) => {
    if (typeof args[0] === "string" && (args[0].includes("No character metrics for") || args[0].includes("KaTeX auto-render"))) {
      return;
    }
    originalWarn.apply(console, args);
  };
}

export default function MathText({ text, className }: { text: string; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const processed = sanitizeMathText(text);

  useEffect(() => {
    if (!ref.current) return;
    try {
      (renderMathInElement as (el: HTMLElement, opts: unknown) => void)(ref.current, {
        delimiters: DELIMITERS,
        throwOnError: false,
        strict: "ignore",
      });
    } catch {
      /* leave as plain text on failure */
    }
  }, [processed]);

  return (
    <div ref={ref} className={`break-words max-w-full ${className ?? ""}`}>
      {processed}
    </div>
  );
}
