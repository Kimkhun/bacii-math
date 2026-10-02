// The 15 limit-lesson explorers, one preset each, all rendered by the generic
// LimitExplorer. A preset is the lesson's example turned into a family: its
// constants become sliders (e.g. sin(5x)/(2x) -> sin(kx)/x).
//
// The browser evaluates `f` only to *draw* — nothing here is graded. The
// limit a preset displays is the closed form from that lesson's formula
// sheet (e.g. lim sin(kx)/x = k), and the hole is drawn at that exact value,
// never at a float sampled near the point. animations/verify_explorers.py
// re-checks every closed form against SymPy.
import type { Translations } from "@/lib/i18n";
import type { Window2D } from "@/lib/plot";

export type Params = Record<string, number>;

export interface ParamSpec {
  key: string;
  /** LaTeX label shown before the slider. */
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
}

export interface LimitPreset {
  params: ParamSpec[];
  /** The point x approaches, or "inf" for x -> +infinity. */
  target: (p: Params) => number | "inf";
  /** Approach from both sides (default) or only from the right (x -> a+). */
  side?: "both" | "right";
  f: (x: number, p: Params) => number;
  /** Exact limit: its value (for drawing) and LaTeX (closed form, then value). */
  limit: (p: Params) => { value: number; latex: string };
  /** LaTeX of the full limit expression, e.g. \lim_{x \to 0} \frac{\sin 3x}{x}. */
  expression: (p: Params) => string;
  window: (p: Params) => Window2D;
  /** Farthest starting distance for the approach slider (finite targets). */
  hMax?: number;
  /** A second curve the student can toggle on (simplified form, numerator, tangent). */
  overlay?: { label: keyof Translations; f: (x: number, p: Params) => number };
  /** Continuous at the point: draw f(a) as a filled dot rather than a hole. */
  continuous?: boolean;
  /** Extra visual panel next to the graph. */
  extra?: "unit-circle";
}

/** Short number for LaTeX: up to `d` decimals, trailing zeros trimmed. */
export function num(v: number, d = 3): string {
  if (!Number.isFinite(v)) return v > 0 ? "+\\infty" : "-\\infty";
  const r = +v.toFixed(d);
  return Object.is(r, -0) ? "0" : String(r);
}

/** `c` as a signed term after another term: "+ 3x", "- x", "" when c = 0. */
function signed(c: number, body = ""): string {
  if (c === 0) return "";
  const mag = Math.abs(c) === 1 && body ? "" : num(Math.abs(c));
  return `${c < 0 ? "-" : "+"} ${mag}${body}`;
}

/** `c` as a leading coefficient: "3x", "-x", "x". */
function coef(c: number, body: string): string {
  if (c === 1) return body;
  if (c === -1) return `-${body}`;
  return `${num(c)}${body}`;
}

/** Approximate value suffix, omitted when the closed form is already that number. */
function approx(latex: string, v: number): string {
  const n = num(v, 4);
  return latex === n ? n : `${latex} \\approx ${n}`;
}

const PI = Math.PI;

export const LIMIT_PRESETS: Record<string, LimitPreset> = {
  direct_substitution: {
    params: [
      { key: "a", label: "a", min: -2, max: 3, step: 0.5, value: 2 },
      { key: "b", label: "b", min: -4, max: 4, step: 1, value: 3 },
      { key: "c", label: "c", min: -5, max: 5, step: 1, value: -1 },
    ],
    target: (p) => p.a,
    f: (x, p) => x * x + p.b * x + p.c,
    limit: (p) => {
      const v = p.a * p.a + p.b * p.a + p.c;
      return { value: v, latex: `f(${num(p.a)}) = ${num(v)}` };
    },
    expression: (p) => `\\lim_{x \\to ${num(p.a)}} \\left(x^2 ${signed(p.b, "x")} ${signed(p.c)}\\right)`,
    window: (p) => {
      const ys = [-4, -2, 0, 2, 4, p.a].map((x) => x * x + p.b * x + p.c);
      return { x_min: -4, x_max: 4, y_min: Math.min(-2, ...ys) - 1, y_max: Math.max(...ys) + 1 };
    },
    hMax: 2.5,
    continuous: true,
  },

  factoring_0_0: {
    params: [{ key: "a", label: "a", min: -3, max: 3, step: 0.5, value: 3 }],
    target: (p) => p.a,
    f: (x, p) => (x * x - p.a * p.a) / (x - p.a),
    limit: (p) => ({ value: 2 * p.a, latex: `2a = ${num(2 * p.a)}` }),
    expression: (p) => `\\lim_{x \\to ${num(p.a)}} \\frac{x^2 - ${num(p.a * p.a)}}{x ${signed(-p.a)}}`,
    window: () => ({ x_min: -5, x_max: 5, y_min: -8, y_max: 8 }),
    hMax: 2.5,
    overlay: { label: "explorer_show_simplified", f: (x, p) => x + p.a },
  },

  rationalization_conjugate_finite: {
    params: [{ key: "a", label: "a", min: 1, max: 9, step: 1, value: 4 }],
    target: (p) => p.a,
    f: (x, p) => (Math.sqrt(x) - Math.sqrt(p.a)) / (x - p.a),
    limit: (p) => {
      const v = 1 / (2 * Math.sqrt(p.a));
      const root = Math.sqrt(p.a);
      const latex = Number.isInteger(root) ? `\\frac{1}{2 \\cdot ${root}} = \\frac{1}{${2 * root}}` : `\\frac{1}{2\\sqrt{${num(p.a)}}}`;
      return { value: v, latex: approx(latex, v) };
    },
    expression: (p) => {
      const root = Math.sqrt(p.a);
      const r = Number.isInteger(root) ? String(root) : `\\sqrt{${num(p.a)}}`;
      return `\\lim_{x \\to ${num(p.a)}} \\frac{\\sqrt{x} - ${r}}{x - ${num(p.a)}}`;
    },
    window: () => ({ x_min: 0, x_max: 12, y_min: 0, y_max: 0.8 }),
    hMax: 3,
    overlay: { label: "explorer_show_simplified", f: (x, p) => 1 / (Math.sqrt(x) + Math.sqrt(p.a)) },
  },

  trig_identity_0_0: {
    params: [],
    target: () => PI / 2,
    f: (x) => (1 - Math.sin(x)) / Math.cos(x) ** 2,
    limit: () => ({ value: 0.5, latex: "\\frac{1}{1 + 1} = \\frac{1}{2}" }),
    expression: () => "\\lim_{x \\to \\frac{\\pi}{2}} \\frac{1 - \\sin x}{\\cos^2 x}",
    window: () => ({ x_min: -0.5, x_max: PI + 0.5, y_min: 0, y_max: 1.4 }),
    hMax: 1.4,
    overlay: { label: "explorer_show_simplified", f: (x) => 1 / (1 + Math.sin(x)) },
  },

  sinc_standard_limit: {
    params: [{ key: "k", label: "k", min: 0.5, max: 6, step: 0.5, value: 1 }],
    target: () => 0,
    f: (x, p) => Math.sin(p.k * x) / x,
    limit: (p) => ({ value: p.k, latex: `k = ${num(p.k)}` }),
    expression: (p) => `\\lim_{x \\to 0} \\frac{\\sin(${coef(p.k, "x")})}{x}`,
    window: (p) => ({ x_min: -6, x_max: 6, y_min: -0.4 * p.k - 0.2, y_max: p.k * 1.25 + 0.2 }),
    hMax: 4,
    extra: "unit-circle",
  },

  angle_addition_0_0: {
    // a sin x + b cos x = R sin(x + phi) vanishes at x0 = -phi (taken in [0, pi));
    // the quotient by (x - x0) then tends to R cos(x0 + phi) = +-R.
    params: [
      { key: "a", label: "a", min: -3, max: 3, step: 0.01, value: 1 },
      { key: "b", label: "b", min: -3, max: 3, step: 0.01, value: -1.73 },
    ],
    target: (p) => rootOf(p),
    f: (x, p) => (p.a * Math.sin(x) + p.b * Math.cos(x)) / (x - rootOf(p)),
    limit: (p) => {
      const R = Math.hypot(p.a, p.b);
      const v = R * Math.cos(rootOf(p) + Math.atan2(p.b, p.a));
      return { value: v, latex: `${v < 0 ? "-" : ""}\\sqrt{a^2 + b^2} \\approx ${num(v)}` };
    },
    expression: (p) =>
      `\\lim_{x \\to ${num(rootOf(p))}} \\frac{${coef(p.a, "\\sin x")} ${signed(p.b, "\\cos x")}}{x - ${num(rootOf(p))}}`,
    window: (p) => {
      const R = Math.max(Math.hypot(p.a, p.b), 0.5);
      return { x_min: -2, x_max: 5, y_min: -R * 1.25, y_max: R * 1.25 };
    },
    hMax: 2.5,
    overlay: { label: "explorer_show_numerator", f: (x, p) => p.a * Math.sin(x) + p.b * Math.cos(x) },
  },

  rationalization_sinc_combo: {
    params: [{ key: "k", label: "k", min: 0.5, max: 4, step: 0.5, value: 2 }],
    target: () => 0,
    f: (x, p) => (Math.sqrt(1 + x) - Math.sqrt(1 - x)) / Math.sin(p.k * x),
    limit: (p) => ({ value: 1 / p.k, latex: approx(`\\frac{1}{k} = \\frac{1}{${num(p.k)}}`, 1 / p.k) }),
    expression: (p) => `\\lim_{x \\to 0} \\frac{\\sqrt{1 + x} - \\sqrt{1 - x}}{\\sin(${coef(p.k, "x")})}`,
    window: (p) => ({ x_min: -1, x_max: 1, y_min: 0, y_max: Math.max(1.5, 2.2 / p.k) }),
    hMax: 0.9,
  },

  exponential_sinc_combo: {
    params: [{ key: "k", label: "k", min: 0.5, max: 4, step: 0.5, value: 3 }],
    target: () => 0,
    f: (x, p) => ((Math.exp(x) + Math.exp(-x)) * Math.sin(p.k * x) ** 2) / (2 * x * x),
    limit: (p) => ({ value: p.k * p.k, latex: `k^2 = ${num(p.k * p.k)}` }),
    expression: (p) => `\\lim_{x \\to 0} \\frac{(e^x + e^{-x})\\sin^2(${coef(p.k, "x")})}{2x^2}`,
    window: (p) => ({ x_min: -2, x_max: 2, y_min: -0.5, y_max: p.k * p.k * 1.2 + 0.5 }),
    hMax: 1.5,
  },

  half_angle_sinc_combo: {
    params: [{ key: "m", label: "m", min: 0.5, max: 6, step: 0.5, value: 4 }],
    target: () => 0,
    f: (x, p) => (1 - Math.cos(p.m * x)) / (x * x),
    limit: (p) => ({ value: (p.m * p.m) / 2, latex: `\\frac{m^2}{2} = ${num((p.m * p.m) / 2)}` }),
    expression: (p) => `\\lim_{x \\to 0} \\frac{1 - \\cos(${coef(p.m, "x")})}{x^2}`,
    window: (p) => ({ x_min: -2, x_max: 2, y_min: -0.3, y_max: (p.m * p.m) / 2 * 1.2 + 0.3 }),
    hMax: 1.5,
  },

  exponential_standard_limit: {
    params: [
      { key: "a", label: "a", min: -4, max: 5, step: 0.5, value: 3 },
      { key: "b", label: "b", min: 0.5, max: 6, step: 0.5, value: 5 },
    ],
    target: () => 0,
    f: (x, p) => (Math.exp(p.a * x) - 1) / (Math.exp(p.b * x) - 1),
    limit: (p) => ({ value: p.a / p.b, latex: approx(`\\frac{a}{b} = \\frac{${num(p.a)}}{${num(p.b)}}`, p.a / p.b) }),
    expression: (p) => `\\lim_{x \\to 0} \\frac{e^{${coef(p.a, "x")}} - 1}{e^{${coef(p.b, "x")}} - 1}`,
    window: (p) => {
      const lo = Math.min(0, p.a / p.b, ...[-1.5, 1.5].map((x) => (Math.exp(p.a * x) - 1) / (Math.exp(p.b * x) - 1)));
      const hi = Math.max(1, p.a / p.b, ...[-1.5, 1.5].map((x) => (Math.exp(p.a * x) - 1) / (Math.exp(p.b * x) - 1)));
      return { x_min: -1.5, x_max: 1.5, y_min: Math.max(lo, -6) - 0.2, y_max: Math.min(hi, 6) + 0.2 };
    },
    hMax: 1.2,
  },

  conjugate_infinity: {
    params: [{ key: "b", label: "b", min: -4, max: 8, step: 1, value: 4 }],
    target: () => "inf",
    f: (x, p) => Math.sqrt(x * x + p.b * x) - x,
    limit: (p) => ({ value: p.b / 2, latex: `\\frac{b}{2} = ${num(p.b / 2)}` }),
    expression: (p) => `\\lim_{x \\to +\\infty} \\left(\\sqrt{x^2 ${signed(p.b, "x")}} - x\\right)`,
    window: (p) => ({ x_min: 0, x_max: 40, y_min: Math.min(0, p.b / 2) - 1, y_max: Math.max(0, p.b / 2) + 1.5 }),
  },

  log_limit_infinity: {
    params: [{ key: "c", label: "c", min: 0.5, max: 6, step: 0.5, value: 2 }],
    target: () => "inf",
    f: (x, p) => x * (Math.log(x + p.c) - Math.log(x)),
    limit: (p) => ({ value: p.c, latex: `c = ${num(p.c)}` }),
    expression: (p) => `\\lim_{x \\to +\\infty} x\\left[\\ln(x + ${num(p.c)}) - \\ln x\\right]`,
    window: (p) => ({ x_min: 0, x_max: 40, y_min: 0, y_max: p.c * 1.5 }),
  },

  rational_function_infinity: {
    params: [
      { key: "n", label: "n", min: 1, max: 3, step: 1, value: 2 },
      { key: "m", label: "m", min: 1, max: 3, step: 1, value: 2 },
      { key: "p", label: "p", min: 1, max: 5, step: 1, value: 3 },
      { key: "q", label: "q", min: 1, max: 5, step: 1, value: 2 },
    ],
    target: () => "inf",
    f: (x, p) => (p.p * x ** p.n + 5 * x) / (p.q * x ** p.m + 7),
    limit: (p) => {
      if (p.n < p.m) return { value: 0, latex: "n < m \\Rightarrow 0" };
      if (p.n > p.m) return { value: Infinity, latex: "n > m \\Rightarrow +\\infty" };
      // Equal degrees: ratio of the leading coefficients (5x joins the top's
      // leading term when n = 1).
      const lead = p.p + (p.n === 1 ? 5 : 0);
      return { value: lead / p.q, latex: approx(`\\frac{${num(lead)}}{${num(p.q)}}`, lead / p.q) };
    },
    expression: (p) =>
      `\\lim_{x \\to +\\infty} \\frac{${coef(p.p, p.n === 1 ? "x" : `x^${p.n}`)} + 5x}{${coef(p.q, p.m === 1 ? "x" : `x^${p.m}`)} + 7}`,
    window: (p) => ({ x_min: 0, x_max: 40, y_min: 0, y_max: p.n === p.m ? Math.max(3, ((p.p + (p.n === 1 ? 5 : 0)) / p.q) * 2) : 6 }),
  },

  log_limit_zero: {
    params: [{ key: "p", label: "p", min: 0.1, max: 2, step: 0.1, value: 1 }],
    target: () => 0,
    side: "right",
    f: (x, p) => x ** p.p * Math.log(x),
    limit: () => ({ value: 0, latex: "0" }),
    expression: (p) => `\\lim_{x \\to 0^+} ${p.p === 1 ? "x" : `x^{${num(p.p)}}`} \\ln x`,
    window: (p) => ({ x_min: -0.1, x_max: 1.5, y_min: -Math.max(0.5, 1 / (Math.E * p.p)) * 1.3, y_max: 0.8 }),
    hMax: 1.4,
  },

  indeterminate_one_infinity: {
    params: [{ key: "k", label: "k", min: -3, max: 4, step: 0.5, value: 3 }],
    target: () => "inf",
    f: (x, p) => (1 + p.k / x) ** x,
    limit: (p) => ({ value: Math.exp(p.k), latex: approx(`e^{${num(p.k)}}`, Math.exp(p.k)) }),
    expression: (p) => {
      const base = p.k === 0 ? "1" : `1 ${p.k < 0 ? "-" : "+"} \\frac{${num(Math.abs(p.k))}}{x}`;
      return `\\lim_{x \\to +\\infty} \\left(${base}\\right)^x`;
    },
    window: (p) => ({ x_min: 0, x_max: 40, y_min: 0, y_max: Math.exp(p.k) * 1.3 + 0.5 }),
  },
};

function rootOf(p: Params): number {
  const phi = Math.atan2(p.b, p.a);
  let x0 = -phi;
  while (x0 < 0) x0 += PI;
  while (x0 >= PI) x0 -= PI;
  return x0;
}
