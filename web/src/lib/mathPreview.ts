// Best-effort SymPy-syntax -> LaTeX conversion, used only for the admin
// sandbox's live "as you type" preview (rendered via MathText/KaTeX). This is
// NOT the source of truth for math — SymPy's own `latex()` (backend
// `engine/core/shared.py`) is, and solve/grade results always show that.
// This converter exists purely so an admin typing "sqrt(2)/2" or "pi/4" into
// a param field sees it rendered as √2⁄2 or π⁄4 instead of raw text, without
// a network round-trip on every keystroke.

const FUNC_WRAPPERS: Record<string, [string, string]> = {
  sqrt: ["\\sqrt{", "}"],
  Abs: ["\\left|", "\\right|"],
  exp: ["e^{", "}"],
  log: ["\\log\\left(", "\\right)"],
  ln: ["\\ln\\left(", "\\right)"],
  sin: ["\\sin\\left(", "\\right)"],
  cos: ["\\cos\\left(", "\\right)"],
  tan: ["\\tan\\left(", "\\right)"],
};

function expandFuncs(s: string): string {
  let out = "";
  let i = 0;
  outer: while (i < s.length) {
    for (const name of Object.keys(FUNC_WRAPPERS)) {
      const isWordStart = i === 0 || !/[A-Za-z0-9_]/.test(s[i - 1]);
      if (isWordStart && s.startsWith(name + "(", i)) {
        let depth = 1;
        let j = i + name.length + 1;
        while (j < s.length && depth > 0) {
          if (s[j] === "(") depth++;
          else if (s[j] === ")") depth--;
          j++;
        }
        const inner = s.slice(i + name.length + 1, j - 1);
        const [before, after] = FUNC_WRAPPERS[name];
        out += before + expandFuncs(inner) + after;
        i = j;
        continue outer;
      }
    }
    out += s[i];
    i++;
  }
  return out;
}

// Finds a top-level (paren-depth 0) occurrence of `ch`, skipping the first
// character so a leading unary +/- isn't mistaken for a split point.
function topLevelIndexOf(s: string, ch: string): number {
  let depth = 0;
  for (let i = 1; i < s.length; i++) {
    const c = s[i];
    if (c === "(" || c === "{") depth++;
    else if (c === ")" || c === "}") depth--;
    else if (depth === 0 && c === ch) return i;
  }
  return -1;
}

function wrapFraction(s: string): string {
  const trimmed = s.trim();
  if (topLevelIndexOf(trimmed, "+") !== -1 || topLevelIndexOf(trimmed, "-") !== -1) return s;
  const slash = topLevelIndexOf(trimmed, "/");
  if (slash === -1) return s;
  const num = trimmed.slice(0, slash).trim();
  const den = trimmed.slice(slash + 1).trim();
  if (!num || !den) return s;
  return `\\frac{${num}}{${den}}`;
}

export function toLatexPreview(input: string): string {
  if (!input || !input.trim()) return "";
  let s = expandFuncs(input);
  s = wrapFraction(s);
  s = s.replace(/\*\*/g, "^");
  s = s.replace(/\bpi\b/g, "\\pi");
  s = s.replace(/\boo\b/g, "\\infty");
  s = s.replace(/\bE\b/g, "e");
  s = s.replace(/\bI\b/g, "i");
  s = s.replace(/\*/g, "\\cdot ");
  s = s.replace(/\^(-?[A-Za-z0-9]+)/g, "^{$1}");
  return s;
}

// True only for values worth rendering as math (skips plain identifiers like
// var="x" or op="add" that the sandbox sends as literal strings — see
// `services._sandbox_coerce` / docs/admin-sandbox.md).
export function looksLikeMath(value: string): boolean {
  return /[0-9+\-*/^(){}]|sqrt|pi\b|oo\b/.test(value);
}
