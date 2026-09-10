"use client";

// A small on-screen calculator keypad for the admin sandbox. It never owns
// any text itself — every button just asks the page to insert a token at
// the caret of whichever field was last focused (see AdminSandbox's
// `insertToken`). Buttons use onMouseDown={preventDefault} so clicking one
// never steals focus away from the field being edited, which is what keeps
// the caret position (and therefore "insert at cursor") working at all.

interface KeyDef {
  label: string;
  token: string;
  /** Caret offset from the end of the inserted token; defaults to the end. */
  caretBack?: number;
  title?: string;
}

const FUNCTION_KEYS: KeyDef[] = [
  { label: "sin", token: "sin(", caretBack: 1, title: "sine" },
  { label: "cos", token: "cos(", caretBack: 1, title: "cosine" },
  { label: "tan", token: "tan(", caretBack: 1, title: "tangent" },
  { label: "log", token: "log(", caretBack: 1, title: "log base 10" },
  { label: "ln", token: "ln(", caretBack: 1, title: "natural log" },
  { label: "√", token: "sqrt(", caretBack: 1, title: "square root" },
  { label: "|x|", token: "Abs(", caretBack: 1, title: "absolute value" },
  { label: "e^x", token: "exp(", caretBack: 1, title: "e to the power" },
  { label: "π", token: "pi", title: "pi" },
  { label: "e", token: "E", title: "Euler's number" },
  { label: "i", token: "I", title: "imaginary unit" },
  { label: "∞", token: "oo", title: "infinity" },
];

const STRUCTURE_KEYS: KeyDef[] = [
  { label: "(", token: "(" },
  { label: ")", token: ")" },
  { label: "x^y", token: "^", title: "power" },
  { label: "x²", token: "^2", title: "squared" },
  { label: "a/b", token: "/", title: "fraction" },
  { label: ",", token: ", " },
  { label: "x", token: "x", title: "variable" },
  { label: "=", token: "=" },
];

const PAD_ROWS: KeyDef[][] = [
  [{ label: "7", token: "7" }, { label: "8", token: "8" }, { label: "9", token: "9" }, { label: "÷", token: "/" }],
  [{ label: "4", token: "4" }, { label: "5", token: "5" }, { label: "6", token: "6" }, { label: "×", token: "*" }],
  [{ label: "1", token: "1" }, { label: "2", token: "2" }, { label: "3", token: "3" }, { label: "−", token: "-" }],
  [{ label: "0", token: "0" }, { label: ".", token: "." }, { label: "⌫", token: "" }, { label: "+", token: "+" }],
];

const keyBtn = "h-9 rounded-md border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 active:bg-slate-100";

export default function MathKeypad({
  onKey,
  onMove,
  onClear,
}: {
  onKey: (token: string, caretBack?: number) => void;
  onMove: (dir: -1 | 1) => void;
  onClear: () => void;
}) {
  const press = (k: KeyDef) => {
    if (k.token === "") return; // backspace handled separately below
    onKey(k.token, k.caretBack);
  };
  const guard = (e: React.MouseEvent) => e.preventDefault();

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm select-none">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Keypad</span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onMouseDown={guard}
            onClick={() => onMove(-1)}
            className="w-7 h-7 rounded border border-slate-200 text-slate-500 hover:bg-slate-50"
            title="Move caret left"
          >
            ←
          </button>
          <button
            type="button"
            onMouseDown={guard}
            onClick={() => onMove(1)}
            className="w-7 h-7 rounded border border-slate-200 text-slate-500 hover:bg-slate-50"
            title="Move caret right"
          >
            →
          </button>
          <button
            type="button"
            onMouseDown={guard}
            onClick={onClear}
            className="px-2 h-7 rounded border border-slate-200 text-xs text-slate-500 hover:bg-slate-50"
            title="Clear this field"
          >
            AC
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-1.5 mb-2">
        {FUNCTION_KEYS.map((k) => (
          <button
            key={k.label}
            type="button"
            title={k.title}
            onMouseDown={guard}
            onClick={() => press(k)}
            className={keyBtn}
          >
            {k.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-4 gap-1.5 mb-2">
        {STRUCTURE_KEYS.map((k) => (
          <button
            key={k.label}
            type="button"
            title={k.title}
            onMouseDown={guard}
            onClick={() => press(k)}
            className={keyBtn}
          >
            {k.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-4 gap-1.5">
        {PAD_ROWS.flat().map((k) => (
          <button
            key={k.label}
            type="button"
            onMouseDown={guard}
            onClick={() => (k.token === "" ? onKey("") : press(k))}
            className={
              k.token === ""
                ? `${keyBtn} text-red-500`
                : /[0-9.]/.test(k.token)
                ? `${keyBtn} font-semibold`
                : `${keyBtn} bg-slate-50`
            }
          >
            {k.label}
          </button>
        ))}
      </div>
    </div>
  );
}
