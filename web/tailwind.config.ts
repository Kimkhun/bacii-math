import type { Config } from "tailwindcss";
import plugin from "tailwindcss/plugin";
import defaultColors from "tailwindcss/colors";

// ---------------------------------------------------------------------------
// Light / dark theming
//
// Components keep writing plain light-theme classes (`bg-white`,
// `text-slate-900`, `bg-red-50 text-red-700`, `border-paper-200` ...). Every
// themed color resolves through a CSS variable instead of a literal, and
// `html.dark` swaps those variables — so the whole app flips without a
// `dark:` variant on every element. Chromatic scales are mirrored
// (50 <-> 950, 100 <-> 900, ...), which keeps every light-mode pairing
// ("light tint background + dark text of the same hue") readable inverted.
//
// Handwriting surfaces are the exception: they stay drawn in light colors and
// are flipped with a CSS filter instead (`.invert-in-dark`, see globals.css),
// so the image the OCR sees is always dark ink on white paper.
// ---------------------------------------------------------------------------

const SHADES = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"] as const;

const CHROMATIC = [
  "gray", "red", "orange", "amber", "yellow", "lime", "green", "emerald", "teal",
  "cyan", "sky", "blue", "indigo", "violet", "purple", "fuchsia", "pink", "rose",
] as const;

type Scale = Record<string, string>;

// Dark-mode surfaces. Ordered by distance from the page, like their light
// counterparts: page < paper-50 panels < white cards < slate-50 insets.
const DARK_PAGE = "#141619";
const DARK_CARD = "#1e2126";

// Slate carries most of the UI chrome, so its dark side is hand-tuned rather
// than mirrored: surfaces stay close to the card, text shades stay readable.
const SLATE_DARK: Scale = {
  "50": "#23272d",
  "100": "#2a2f36",
  "200": "#353b44",
  "300": "#48505b",
  "400": "#727b88",
  "500": "#949dab",
  "600": "#b2bac6",
  "700": "#cbd2dc",
  "800": "#dfe4eb",
  "900": "#edf0f4",
  "950": "#f8fafc",
};

// The warm "paper" neutrals of the practice page and its toolbars.
const PAPER_LIGHT: Scale = {
  "25": "#fdfcf8",
  "50": "#faf9f6",
  "100": "#f2f1ed",
  "150": "#eae7df",
  "200": "#e4e2db",
  "300": "#dddad1",
  "400": "#c7c2b6",
  "500": "#a8a296",
  "600": "#8a857b",
  "700": "#6b6558",
  "800": "#3f3c35",
};
const PAPER_DARK: Scale = {
  "25": "#1b1d21",
  "50": "#1a1c20",
  "100": DARK_PAGE,
  "150": "#2b2e33",
  "200": "#30333a",
  "300": "#3b3f46",
  "400": "#575b63",
  "500": "#7e8189",
  "600": "#9b9ea5",
  "700": "#b6b8bd",
  "800": "#d8d9dc",
};

// Near-black ink used for primary buttons, tooltips and headline text.
const INK_LIGHT = { DEFAULT: "#23272e", soft: "#31363f" };
const INK_DARK = { DEFAULT: "#eceef1", soft: "#d9dce1" };

function rgb(hex: string): string {
  const n = parseInt(hex.replace("#", ""), 16);
  return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`;
}

function mix(a: string, b: string, t: number): string {
  const [ar, ag, ab] = rgb(a).split(" ").map(Number);
  const [br, bg, bb] = rgb(b).split(" ").map(Number);
  const c = (x: number, y: number) => Math.round(x + (y - x) * t).toString(16).padStart(2, "0");
  return `#${c(ar, br)}${c(ag, bg)}${c(ab, bb)}`;
}

// Mirror a Tailwind scale. The deepest shades become tinted panel
// backgrounds, so they are eased toward the card color to read as a soft
// tint rather than a saturated block.
function mirrored(scale: Scale): Scale {
  const out: Scale = {};
  SHADES.forEach((s, i) => {
    out[s] = scale[SHADES[SHADES.length - 1 - i]];
  });
  out["50"] = mix(out["50"], DARK_CARD, 0.45);
  out["100"] = mix(out["100"], DARK_CARD, 0.3);
  return out;
}

const palette = (name: string, keys: readonly string[]) =>
  Object.fromEntries(keys.map((k) => [k, `rgb(var(--c-${name}-${k}) / <alpha-value>)`]));

function vars(theme: "light" | "dark"): Record<string, string> {
  const dark = theme === "dark";
  const v: Record<string, string> = {};
  const put = (name: string, scale: Scale) => {
    for (const [k, hex] of Object.entries(scale)) v[`--c-${name}-${k}`] = rgb(hex);
  };
  const tw = defaultColors as unknown as Record<string, Scale>;
  put("slate", dark ? SLATE_DARK : tw.slate);
  for (const name of CHROMATIC) put(name, dark ? mirrored(tw[name]) : tw[name]);
  put("paper", dark ? PAPER_DARK : PAPER_LIGHT);
  put("ink", dark ? INK_DARK : INK_LIGHT);
  v["--c-white-DEFAULT"] = rgb(dark ? DARK_CARD : "#ffffff");
  v["--c-page-DEFAULT"] = rgb(dark ? DARK_PAGE : PAPER_LIGHT["100"]);
  return v;
}

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        white: palette("white", ["DEFAULT"]).DEFAULT,
        page: palette("page", ["DEFAULT"]).DEFAULT,
        slate: palette("slate", SHADES),
        ...Object.fromEntries(CHROMATIC.map((name) => [name, palette(name, SHADES)])),
        paper: palette("paper", Object.keys(PAPER_LIGHT)),
        ink: palette("ink", ["DEFAULT", "soft"]),
      },
    },
  },
  plugins: [
    // `stylus:` — larger hit targets for touch/pen input (tablets, iPad +
    // Apple Pencil) without bloating buttons for precise mouse users.
    plugin(({ addVariant }) => {
      addVariant("stylus", "@media (pointer: coarse)");
    }),
    // Theme variables. Inside `.invert-in-dark` the light values are restored
    // so a handwriting surface renders exactly as in light mode before the
    // CSS filter flips it.
    plugin(({ addBase }) => {
      addBase({
        ":root, .dark .invert-in-dark": vars("light"),
        ".dark": vars("dark"),
      });
    }),
  ],
};

export default config;
