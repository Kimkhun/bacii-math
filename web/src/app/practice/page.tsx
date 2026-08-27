"use client";

import { ReactNode, Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import AuthGuard from "@/components/AuthGuard";
import Canvas, { CanvasExportMap, CanvasHandle, CanvasTool, FULL_W, LineSnapshot, PEN_WIDTHS } from "@/components/Canvas";
import MathText from "@/components/MathText";
import DisambiguationCard, { DisambiguationCandidate } from "@/components/DisambiguationCard";
import FunctionGraph from "@/components/FunctionGraph";
import { api, Question, GradeResult, Explanation, DetectResult, SessionSummary, FormulaEntry, GraphGradeResult, StrokeDoc } from "@/lib/api";
import { getStreak, playGradeSound, playMarkSound, updateStreak } from "@/lib/sounds";

const CURSIVE = "'Caveat', 'Segoe Script', cursive";

const MARK_STAGGER_MS = 1000;

// Keyframes for the red-pen marks + line pops (shared by every part's canvas).
const MARKS_STYLE = `
  @keyframes mark-pop {
    0% { opacity: 0; transform: scale(0.4); }
    35% { opacity: 1; transform: scale(1.4); }
    60% { transform: scale(0.95); }
    100% { opacity: 1; transform: scale(1); }
  }
  .mark-pop {
    opacity: 0;
    animation: mark-pop 0.45s ease-out forwards;
    transform-box: fill-box;
    transform-origin: center;
  }
  @keyframes line-grow {
    0% { transform: scale(1); }
    40% { transform: scale(1.35); }
    100% { transform: scale(1); }
  }
  .line-grow {
    transform-box: fill-box;
    transform-origin: center;
    animation: line-grow 0.45s ease-out;
  }
`;

// Per-line verdicts in page order, for scheduling the reveal sounds.
function markEvents(det: DetectResult, res: GradeResult): { correct: boolean }[] {
  const check = res.step_check;
  if (!check) return [];
  const events: { correct: boolean }[] = [];
  (det.lines ?? []).forEach((_, i) => {
    const lineRes = check.line_results.find((r) => r.line === i + 1);
    if (lineRes && lineRes.checked) events.push({ correct: !!lineRes.correct });
  });
  return events;
}

// Values are plain `question_type` strings for topics where that's the only
// axis of variety (complex, functions). For topics whose real variety is a
// *technique*/*scenario* one level below question_type (limit's techniques,
// probability's scenario catalog, integral's per-kind variants), the value is
// encoded as "<question_type>:<variant>" — see splitTypeValue().
const TYPE_OPTIONS: Record<string, { value: string; label: string }[]> = {
  complex: [
    { value: "modulus", label: "Modulus" },
    { value: "argument", label: "Argument" },
    { value: "conjugate", label: "Conjugate" },
    { value: "real_part", label: "Real part" },
    { value: "imaginary_part", label: "Imaginary part" },
  ],
  limit: [
    { value: "limit:direct_substitution", label: "Direct substitution" },
    { value: "limit:factoring_0_0", label: "Factoring (0/0)" },
    { value: "limit:rationalization_conjugate_finite", label: "Conjugate rationalization" },
    { value: "limit:sinc_standard_limit", label: "Standard limit sin(x)/x" },
    { value: "limit:exponential_standard_limit", label: "Standard limit (eˣ-1)/x" },
    { value: "limit:rationalization_sinc_combo", label: "Conjugate + sinc combo" },
    { value: "limit:exponential_sinc_combo", label: "Exponential + sinc combo" },
    { value: "limit:half_angle_sinc_combo", label: "Half-angle + sinc combo" },
    { value: "limit:rational_function_infinity", label: "Rational function at infinity" },
    { value: "limit:conjugate_infinity", label: "Conjugate at infinity" },
    { value: "limit:log_limit_infinity", label: "Logarithmic limit at infinity" },
  ],
  integral: [
    { value: "definite_integral", label: "Definite integral (any)" },
    { value: "definite_integral:polynomial", label: "Definite — polynomial" },
    { value: "definite_integral:linear_argument", label: "Definite — linear argument" },
    { value: "definite_integral:mixed_sum", label: "Definite — mixed sum" },
    { value: "definite_integral:trig", label: "Definite — trig" },
    { value: "definite_integral:u_substitution", label: "Definite — u-substitution" },
    { value: "definite_integral:by_parts", label: "Definite — by parts" },
    { value: "indefinite_integral", label: "Indefinite integral (any)" },
    { value: "indefinite_integral:power", label: "Indefinite — power" },
    { value: "indefinite_integral:expand", label: "Indefinite — expand" },
    { value: "indefinite_integral:split", label: "Indefinite — split" },
    { value: "indefinite_integral:linear_argument", label: "Indefinite — linear argument" },
    { value: "indefinite_integral:usub", label: "Indefinite — u-substitution" },
    { value: "indefinite_integral:trig_sec", label: "Indefinite — trig (sec²)" },
  ],
  probability: [
    { value: "probability:exercise_bag_split_atleast", label: "Balls from a bag" },
    { value: "probability:exercise_two_bag_odd_even", label: "Two bags of numbered balls" },
    { value: "probability:exercise_two_box_colors", label: "Two boxes of colors" },
    { value: "probability:exercise_banknotes", label: "Banknotes" },
    { value: "probability:exercise_pens", label: "Pens" },
    { value: "probability:exercise_students", label: "Students" },
  ],
  functions: [{ value: "study", label: "Curve study & area" }],
};

// Splits a TYPE_OPTIONS value into the {question_type, variant} pair the
// generate API actually wants (see the TYPE_OPTIONS comment above).
function splitTypeValue(value: string): { question_type?: string; variant?: string } {
  const i = value.indexOf(":");
  if (i === -1) return { question_type: value };
  return { question_type: value.slice(0, i), variant: value.slice(i + 1) };
}

interface AmbiguousLine {
  index: number;
  primary: DisambiguationCandidate;
  candidates: DisambiguationCandidate[];
}

interface SessionConfig {
  mode: string;
  topic: string;
  questionType: string;
  difficulty: string;
}

// Snapshot of one part's canvas-adjacent state, captured when navigating away
// from a question so it can be restored verbatim on return.
interface PartState {
  typed: string;
  detected: string | null;
  workText: string | null;
  workLatex: string[] | null;
  detectResult: DetectResult | null;
  result: GradeResult | null;
  marks: ReactNode[] | null;
  linePops: ReactNode[] | null;
  // Raw ink snapshot (data URL), captured whenever navigating away from a
  // part that hasn't been graded yet — grading already preserves the look of
  // the work via `marks`/`linePops`, but ungraded strokes have nothing else
  // recording them. Restored via Canvas.loadBackgroundInk() so the student
  // can keep writing on top of it instead of landing on a frozen image.
  canvasImage?: string | null;
}

// Re-draw a past attempt's OCR'd writing at its stored box positions. The text
// is squashed to fit its original box (lengthAdjust) so it reads as it did on
// the page. Cursive font keeps the "handwritten" feel without storing images.
// Each line pops in with the expand animation (mark-pop), so the whole line of
// writing grows with its correction.
function buildWriting(det: { lines: string[]; lines_boxes?: (number[] | null)[] }, map: CanvasExportMap): ReactNode[] {
  const nodes: ReactNode[] = [];
  (det.lines ?? []).forEach((ln, i) => {
    const b = det.lines_boxes?.[i];
    if (!b || b.length !== 4) return;
    const x = map.offsetX + b[0] * map.scale;
    const y = map.offsetY + b[1] * map.scale;
    const w = (b[2] - b[0]) * map.scale;
    const h = (b[3] - b[1]) * map.scale;
    const fs = Math.min(Math.max(20, h * 0.7), 60);
    nodes.push(
      <g key={`w-${i}`} className="mark-pop" style={{ animationDelay: `${i * MARK_STAGGER_MS}ms` }}>
        <text
          x={x + 6}
          y={y + h * 0.78}
          fontSize={fs}
          fill="#1f2937"
          fontFamily={CURSIVE}
          textLength={Math.max(10, w - 12)}
          lengthAdjust="spacingAndGlyphs"
        >
          {ln}
        </text>
      </g>
    );
  });
  return nodes;
}

// Red-pen marks drawn in canvas-internal coordinates. Progressive reveal is
// handled by the .mark-pop animation (staggered via animation-delay). Every
// text mark carries a white halo so it stays readable even if it brushes the
// student's ink, and marks are placed in free space (right of the line, else
// left, else below) so they never sit on top of the handwriting.
function buildMarks(
  det: DetectResult,
  res: GradeResult,
  map: CanvasExportMap,
  debug = false
): ReactNode[] {
  const nodes: ReactNode[] = [];
  const lines = det.lines ?? [];
  const boxes = det.lines_boxes ?? [];
  const check = res.step_check;

  const rectOf = (i: number) => {
    const b = boxes[i];
    if (!b || b.length !== 4) return null;
    return {
      x1: map.offsetX + b[0] * map.scale,
      y1: map.offsetY + b[1] * map.scale,
      x2: map.offsetX + b[2] * map.scale,
      y2: map.offsetY + b[3] * map.scale,
    };
  };

  // Pick a spot for a mark of the given width: right of the line, else left of
  // it, else below it. Never inside the line's own box.
  const spotFor = (r: { x1: number; x2: number; y1: number; y2: number }, w: number) => {
    if (r.x2 + 16 + w <= map.canvasW - 8) return { x: r.x2 + 16, y: (r.y1 + r.y2) / 2, anchor: "start" as const };
    if (r.x1 - 16 - w >= 8) return { x: r.x1 - 16, y: (r.y1 + r.y2) / 2, anchor: "end" as const };
    return { x: r.x1, y: r.y2 + 22, anchor: "start" as const };
  };

  const halo = {
    paintOrder: "stroke",
    stroke: "#ffffff",
    strokeWidth: 6,
    strokeLinejoin: "round",
  } as const;

  lines.forEach((_, i) => {
    const r = rectOf(i);
    if (!r) return;
    const lineRes = check?.line_results.find((r2) => r2.line === i + 1);
    const h = r.y2 - r.y1;
    const fs = Math.min(Math.max(22, h * 0.85), 42);
    const delay = { animationDelay: `${i * MARK_STAGGER_MS}ms` };

    // Debug: draw every detected line's box with its number and OCR text,
    // color-coded by verdict, so misalignment/merges are visible instantly.
    if (debug) {
      const vColor =
        !lineRes || !lineRes.checked ? "#9ca3af" : lineRes.correct ? "#16a34a" : "#dc2626";
      nodes.push(
        <g key={`dbg-${i}`}>
          <rect
            x={r.x1}
            y={r.y1}
            width={r.x2 - r.x1}
            height={r.y2 - r.y1}
            fill="none"
            stroke={vColor}
            strokeWidth={2.5}
            strokeDasharray="8 5"
          />
          <text
            x={r.x1 + 4}
            y={Math.max(24, r.y1 - 12)}
            fontSize={26}
            fontWeight={800}
            fill={vColor}
            {...halo}
          >
            {i + 1}
          </text>
          {det.lines?.[i] && (
            <text
              x={r.x1}
              y={r.y2 + 24}
              fontSize={22}
              fill={vColor}
              fontFamily="ui-monospace, monospace"
              {...halo}
            >
              {det.lines[i]}
            </text>
          )}
        </g>
      );
    }

    if (!lineRes || !lineRes.checked) return; // skipped (given/unparsed) -> no mark

    if (lineRes.correct) {
      const spot = spotFor(r, 28);
      nodes.push(
        <g key={i} className="mark-pop" style={delay}>
          <text
            x={spot.x}
            y={spot.y + fs * 0.35}
            fontSize={fs}
            fontWeight={800}
            fill="#16a34a"
            textAnchor={spot.anchor}
            {...halo}
          >
            ✓
          </text>
        </g>
      );
    } else {
      const label = lineRes.formula ? lineRes.formula.replaceAll("_", " ") : null;
      const lfs = Math.min(Math.max(16, h * 0.5), 24);
      const lw = label ? label.length * lfs * 0.55 : 0;
      const spot = spotFor(r, 36 + lw);
      const start = spot.anchor === "start";
      const symX = start ? spot.x : spot.x - lw - 42;
      const labelX = start ? spot.x + 38 : spot.x - 6;
      nodes.push(
        <g key={i} className="mark-pop" style={delay}>
          <ellipse
            cx={(r.x1 + r.x2) / 2}
            cy={(r.y1 + r.y2) / 2}
            rx={(r.x2 - r.x1) / 2 + 10}
            ry={h / 2 + 8}
            fill="none"
            stroke="#dc2626"
            strokeWidth={3.5}
          />
          <text
            x={symX}
            y={spot.y + fs * 0.35}
            fontSize={fs}
            fontWeight={800}
            fill="#dc2626"
            textAnchor={spot.anchor}
            {...halo}
          >
            ✗
          </text>
          {label && (
            <text
              x={labelX}
              y={spot.y + lfs * 0.35}
              fontSize={lfs}
              fill="#dc2626"
              fontFamily={CURSIVE}
              fontWeight={700}
              textAnchor={start ? "start" : "end"}
              {...halo}
            >
              {label}
            </text>
          )}
        </g>
      );
    }
  });

  // Teacher-style stamp, written in the same canvas coordinate space.
  if (res.correct) {
    nodes.push(
      <text
        key="stamp"
        className="mark-pop"
        x={map.canvasW - 28}
        y={70}
        textAnchor="end"
        fill="#16a34a"
        fontSize={46}
        fontWeight={800}
        fontFamily={CURSIVE}
        {...halo}
      >
        ✓ Correct!
      </text>
    );
  } else {
    const err = check?.first_error_line;
    const r = err ? rectOf(err - 1) : null;
    if (r) {
      nodes.push(
        <text
          key="stamp"
          className="mark-pop"
          style={{ animationDelay: `${lines.length * MARK_STAGGER_MS}ms` }}
          x={r.x1}
          y={r.y2 + 48}
          fill="#dc2626"
          fontSize={32}
          fontWeight={800}
          fontFamily={CURSIVE}
          {...halo}
        >
          Check line {err}
        </text>
      );
    } else {
      nodes.push(
        <text
          key="stamp"
          className="mark-pop"
          x={map.canvasW - 28}
          y={70}
          textAnchor="end"
          fill="#dc2626"
          fontSize={46}
          fontWeight={800}
          fontFamily={CURSIVE}
          {...halo}
        >
          ✗ Incorrect
        </text>
      );
    }
  }

  return nodes;
}

export default function PracticePage() {
  return (
    <Suspense fallback={null}>
      <PracticeInner />
    </Suspense>
  );
}

const TOOLBAR_POS_KEY = "bacii:toolbarPos";

function PracticeInner() {
  const canvasRefs = useRef<(CanvasHandle | null)[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const pendingDetectRef = useRef<DetectResult | null>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);
  const toolbarDraggingRef = useRef(false);
  const toolbarDragOffsetRef = useRef({ x: 0, y: 0 });

  const [question, setQuestion] = useState<Question | null>(null);
  const [partIndex, setPartIndex] = useState(0);
  const [exerciseDone, setExerciseDone] = useState(false);

  // Practice config (defaults until the student picks something and generates).
  const [mode, setMode] = useState("templates");
  const [topic, setTopic] = useState("complex");
  const [questionType, setQuestionType] = useState("any");
  const [difficulty, setDifficulty] = useState("medium");

  // Per-part state: every sub-part (A/B/C/...) owns its own canvas, typed
  // answer, OCR result, and red-pen marks. Single-part topics use index 0.
  const [typedByPart, setTypedByPart] = useState<string[]>([]);
  const [detectedByPart, setDetectedByPart] = useState<(string | null)[]>([]);
  const [workTextByPart, setWorkTextByPart] = useState<(string | null)[]>([]);
  const [workLatexByPart, setWorkLatexByPart] = useState<(string[] | null)[]>([]);
  const [detectResultByPart, setDetectResultByPart] = useState<(DetectResult | null)[]>([]);
  const [resultByPart, setResultByPart] = useState<(GradeResult | null)[]>([]);
  const [marksByPart, setMarksByPart] = useState<(ReactNode[] | null)[]>([]);
  const [linePopsByPart, setLinePopsByPart] = useState<(ReactNode[] | null)[]>([]);

  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [graphGrade, setGraphGrade] = useState<GraphGradeResult | null>(null);
  const [hintLevel, setHintLevel] = useState(0);
  const [ambiguityQueue, setAmbiguityQueue] = useState<AmbiguousLine[] | null>(null);
  const [ambiguityResolved, setAmbiguityResolved] = useState<Record<number, DisambiguationCandidate>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [debug, setDebug] = useState(false);
  const [tool, setTool] = useState<CanvasTool>("pen");
  const [penWidth, setPenWidth] = useState<number>(PEN_WIDTHS.medium);
  const [eraserWidth, setEraserWidth] = useState<number>(32);
  const [gridStep, setGridStep] = useState<{ x: number; y: number }>({ x: 1, y: 1 });
  const [gridScale, setGridScale] = useState(40);
  const [gridOn, setGridOn] = useState(false);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [streak, setStreak] = useState(0);
  // null = docked centered-bottom (default). Once dragged, an explicit
  // top-left pixel position takes over and is remembered per device.
  const [toolbarPos, setToolbarPos] = useState<{ x: number; y: number } | null>(null);
  const [reviewMode, setReviewMode] = useState(false);
  const [practicingFormula, setPracticingFormula] = useState<{ id: string; name: string } | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();

  // Multi-part probability: the exercise shows all parts together, but each
  // part has its OWN canvas; the top widget switches between them.
  const partLabels: string[] =
    question?.params?.parts?.map((p: any) => (p as { label?: string }).label ?? "").filter(Boolean) ?? [];
  const currentPart = partLabels.length ? partLabels[Math.min(partIndex, partLabels.length - 1)] : null;

  // Write the idx-th slot of a per-part array, growing it as needed. The
  // conditional type extracts the array's element type (e.g. `string | null` for
  // `(string | null)[]`) so callers can pass null without inference fights.
  const setAt = <T extends unknown[]>(
    setter: React.Dispatch<React.SetStateAction<T>>,
    idx: number,
    value: T extends (infer E)[] ? E : never,
  ) => {
    setter((arr) => {
      const next = arr.slice() as (T extends (infer E)[] ? E : never)[];
      while (next.length <= idx) next.push(undefined as never);
      next[idx] = value;
      return next as unknown as T;
    });
  };

  // Per-part setters that target the current part. The setter helpers capture
  // partIndex from the render they were created in, which is the right slot:
  // check() grades part A and writes to A's slot, then advances.
  const setTyped = (v: string) => setAt(setTypedByPart, partIndex, v);
  const setDetected = (v: string | null) => setAt(setDetectedByPart, partIndex, v);
  const setWorkText = (v: string | null) => setAt(setWorkTextByPart, partIndex, v);
  const setWorkLatex = (v: string[] | null) => setAt(setWorkLatexByPart, partIndex, v);
  const setDetectResult = (v: DetectResult | null) => setAt(setDetectResultByPart, partIndex, v);
  const setResult = (v: GradeResult | null) => setAt(setResultByPart, partIndex, v);
  const setMarks = (v: ReactNode[] | null) => setAt(setMarksByPart, partIndex, v);
  const setLinePops = (v: ReactNode[] | null) => setAt(setLinePopsByPart, partIndex, v);

  // Current-part views (the rest of the page reads `typed`, `result`, ... as
  // before — they now resolve to the active part's slot).
  const typed = typedByPart[partIndex] ?? "";
  const detected = detectedByPart[partIndex] ?? null;
  const workText = workTextByPart[partIndex] ?? null;
  const workLatex = workLatexByPart[partIndex] ?? null;
  const detectResult = detectResultByPart[partIndex] ?? null;
  const result = resultByPart[partIndex] ?? null;
  const marks = marksByPart[partIndex] ?? null;
  const linePops = linePopsByPart[partIndex] ?? null;

  const activeCanvas = () => canvasRefs.current[partIndex] ?? null;

  const initPartState = (n: number, start = 0) => {
    const m = Math.max(1, n);
    setPartIndex(Math.min(start, m - 1));
    setExerciseDone(false);
    setTypedByPart(Array(m).fill(""));
    setDetectedByPart(Array(m).fill(null));
    setWorkTextByPart(Array(m).fill(null));
    setWorkLatexByPart(Array(m).fill(null));
    setDetectResultByPart(Array(m).fill(null));
    setResultByPart(Array(m).fill(null));
    setMarksByPart(Array(m).fill(null));
    setLinePopsByPart(Array(m).fill(null));
    setExplanation(null);
    setHintLevel(0);
    setAmbiguityQueue(null);
    setAmbiguityResolved({});
    setError("");
  };

  const setActivePart = (i: number) => {
    setPartIndex(i);
    setExplanation(null);
    setError("");
    // Each part's canvas owns its own grid — reflect it in the toolbar flag.
    setGridOn(canvasRefs.current[i]?.hasGrid() ?? false);
  };

  useEffect(() => {
    setStreak(getStreak());
  }, []);

  // Review mode: /practice?attempt=<id> loads a past attempt and re-draws the
  // student's OCR'd writing at its original positions on the (still live) canvas.
  useEffect(() => {
    const attemptId = searchParams.get("attempt");
    if (!attemptId) return;
    (async () => {
      setBusy(true);
      try {
        const d = await api.attempt(attemptId);
        if (d.question) {
          // The attempt is for one sub-part; rebuild the parts list from the
          // persisted per-part verdicts so the switcher + per-part canvases work.
          const labels = (d.step_check as any)?.parts?.map((p: any) => p.label) ?? [];
          setQuestion({
            id: d.question.id,
            topic: d.question.topic,
            question_type: d.question.question_type,
            difficulty: d.question.difficulty,
            params: { parts: labels.map((l: string) => ({ label: l })) },
            prompt: d.question.prompt,
            prompt_latex: d.question.prompt_latex,
            z_display: "",
            source: "review",
            formula_tags: d.question.formula_tags,
            formula_difficulty: undefined,
          });
          const pi = labels.indexOf((d.step_check as any)?.parts?.[0]?.label);
          initPartState(labels.length, pi >= 0 ? pi : 0);
          setAt(setResultByPart, pi >= 0 ? pi : 0, {
            attempt_id: d.id,
            correct: d.correct,
            reason: d.reason,
            expected: d.question.expected_answer,
            given: d.parsed_answer ?? undefined,
            step_check: d.step_check ?? undefined,
          });
        }
        if (d.work_text) {
          const lines = d.work_text.split("\n");
          setAt(setWorkTextByPart, partIndex, d.work_text);
          setAt(setWorkLatexByPart, partIndex, null);
          const map = activeCanvas()?.getExportMap();
          if (map && d.lines_boxes?.length) {
            const det = { lines, lines_boxes: d.lines_boxes } as DetectResult;
            const pseudo = { correct: d.correct, step_check: d.step_check } as GradeResult;
            setAt(setMarksByPart, partIndex, [...buildWriting(det, map), ...buildMarks(det, pseudo, map, false)]);
          }
        }
        if (d.explanations.length) {
          setExplanation({
            content: d.explanations[0].content,
            provider: d.explanations[0].provider,
            intervened: false,
            trigger: d.explanations[0].trigger,
            step_check: d.step_check ?? undefined,
          });
        }
        if (d.strokes) setPendingStrokes([d.strokes]);
        setReviewMode(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load attempt");
      } finally {
        setBusy(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // Forced formula practice: /practice?formula=<id> (from the formula sheet's
  // "Practice" link, or a post-grade "Practice this" prompt) looks up the
  // formula's known generator variants and forces the first one, loading it
  // straight into the canvas. Falls back to a normal random question if the
  // formula has no known variant (e.g. it's curated-only).
  useEffect(() => {
    const formulaId = searchParams.get("formula");
    if (!formulaId) return;
    (async () => {
      setError("");
      setBusy(true);
      try {
        const catalog = await api.formulas();
        let entry: FormulaEntry | undefined;
        for (const t of catalog.topics) {
          entry = t.entries.find((e) => e.id === formulaId);
          if (entry) break;
        }
        const ref = entry?.variants?.[0];
        const cfg: SessionConfig = ref
          ? {
              mode: "templates",
              topic: ref.topic,
              questionType: ref.variant ? `${ref.question_type}:${ref.variant}` : ref.question_type,
              difficulty: ref.difficulty,
            }
          : { mode, topic, questionType: "any", difficulty };
        // Keep the topic/type/difficulty dropdowns in sync with the forced
        // config — they read from this state, and "New question" reuses it.
        setMode(cfg.mode);
        setTopic(cfg.topic);
        setQuestionType(cfg.questionType);
        setDifficulty(cfg.difficulty);
        const q = await generateQuestion(cfg);
        loadQuestion(q);
        setPracticingFormula({ id: formulaId, name: entry?.name_en ?? formulaId.replaceAll("_", " ") });
        router.replace("/practice");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start formula practice");
      } finally {
        setBusy(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const selectTool = (t: CanvasTool) => {
    setTool(t);
    canvasRefs.current.forEach((c) => c?.setTool(t));
  };

  const selectPenWidth = (w: number) => {
    setPenWidth(w);
    canvasRefs.current.forEach((c) => c?.setPenWidth(w));
  };

  const selectEraserWidth = (w: number) => {
    setEraserWidth(w);
    canvasRefs.current.forEach((c) => c?.setEraserWidth(w));
  };

  // Axes is a drawing tool: selecting it spawns the grid (if absent) and
  // enters axes-edit mode (tap the canvas to move the origin, use the toolbar
  // scale/Δ controls to resize). Clicking it again while in axes mode hides the
  // grid and returns to the pen.
  const selectAxes = () => {
    const c = activeCanvas();
    if (!c) return;
    if (tool === "axes" && gridOn) {
      c.hideGrid();
      setGridOn(false);
      selectTool("pen");
      return;
    }
    if (!gridOn) {
      c.spawnGrid(gridStep.x, gridStep.y, null, gridScale);
      setGridOn(true);
    }
    selectTool("axes");
    markDirty();
  };

  const changeGridStep = (axis: "x" | "y", v: number) => {
    if (!Number.isFinite(v)) return;
    const val = Math.max(0.5, Math.min(50, v));
    setGridStep((s) => {
      const next = { ...s, [axis]: val };
      if (gridOn) activeCanvas()?.setGridSteps(next.x, next.y);
      return next;
    });
  };

  const changeGridScale = (v: number) => {
    if (!Number.isFinite(v)) return;
    const val = Math.max(10, Math.min(200, v));
    setGridScale(val);
    if (gridOn) activeCanvas()?.setGridScale(val);
  };

  const undo = () => {
    activeCanvas()?.undo();
    markDirty();
  };
  const redo = () => {
    activeCanvas()?.redo();
    markDirty();
  };

  const markDirty = () => {
    setCanUndo(activeCanvas()?.canUndo() ?? false);
    setCanRedo(activeCanvas()?.canRedo() ?? false);
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        redo();
        return;
      }
      const k = e.key.toLowerCase();
      if (k === "p") {
        selectTool("pen");
      } else if (k === "e") {
        selectTool("eraser");
      } else if (k === "r") {
        selectTool("ruler");
      } else if (k === "g") {
        selectAxes();
      } else if (k === "c") {
        selectTool("curve");
      } else if (k === "o") {
        selectTool("ellipse");
      } else if (k === "[") {
        if (tool === "eraser") selectEraserWidth(Math.max(10, eraserWidth - 1));
        else selectPenWidth(Math.max(1, penWidth - 1));
      } else if (k === "]") {
        if (tool === "eraser") selectEraserWidth(Math.min(100, eraserWidth + 1));
        else selectPenWidth(Math.min(30, penWidth + 1));
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tool, penWidth, eraserWidth, gridOn]);

  // Once the user has picked a zoom level themselves (buttons or pinch),
  // stop auto-fitting on resize/rotation so we never yank the view out from
  // under them mid-write.
  const userZoomedRef = useRef(false);
  const zoomIn = () => {
    userZoomedRef.current = true;
    setZoom((z) => Math.min(2.5, Math.round((z + 0.25) * 100) / 100));
  };
  const zoomOut = () => {
    userZoomedRef.current = true;
    setZoom((z) => Math.max(0.5, Math.round((z - 0.25) * 100) / 100));
  };
  const zoomReset = () => setZoom(1);
  const onCanvasZoomChange = (z: number) => {
    userZoomedRef.current = true;
    setZoom(z);
  };

  // Tablet-first default: fit the page to the screen width on open, like a
  // notes app does, instead of dropping the user into a 100%-zoom page they
  // have to scroll sideways just to see the margin.
  useEffect(() => {
    const fitToWidth = () => {
      if (userZoomedRef.current) return;
      const available = window.innerWidth - 48;
      const fit = Math.min(1, Math.max(0.5, Math.floor((available / FULL_W) * 20) / 20));
      setZoom(fit);
    };
    fitToWidth();
    window.addEventListener("resize", fitToWidth);
    window.addEventListener("orientationchange", fitToWidth);
    return () => {
      window.removeEventListener("resize", fitToWidth);
      window.removeEventListener("orientationchange", fitToWidth);
    };
  }, []);

  // Keep the (movable) toolbar fully on-screen, using its actual measured size.
  const clampToolbarPos = (x: number, y: number) => {
    const el = toolbarRef.current;
    const w = el?.offsetWidth ?? 320;
    const h = el?.offsetHeight ?? 56;
    const maxX = Math.max(8, window.innerWidth - w - 8);
    const maxY = Math.max(8, window.innerHeight - h - 8);
    return { x: Math.min(Math.max(8, x), maxX), y: Math.min(Math.max(8, y), maxY) };
  };

  // Restore a remembered position (per device) on mount, and re-clamp on resize
  // so the toolbar never ends up stranded off-screen after a viewport change.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(TOOLBAR_POS_KEY);
      if (raw) {
        const p = JSON.parse(raw);
        if (typeof p?.x === "number" && typeof p?.y === "number") setToolbarPos(clampToolbarPos(p.x, p.y));
      }
    } catch {
      /* ignore malformed/unavailable storage */
    }
    const onResize = () => setToolbarPos((p) => (p ? clampToolbarPos(p.x, p.y) : p));
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startToolbarDrag = (e: React.PointerEvent) => {
    e.preventDefault();
    const el = toolbarRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    toolbarDragOffsetRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    toolbarDraggingRef.current = true;
    (e.target as Element).setPointerCapture?.(e.pointerId);
  };

  const moveToolbarDrag = (e: React.PointerEvent) => {
    if (!toolbarDraggingRef.current) return;
    const { x, y } = toolbarDragOffsetRef.current;
    setToolbarPos(clampToolbarPos(e.clientX - x, e.clientY - y));
  };

  const endToolbarDrag = () => {
    if (!toolbarDraggingRef.current) return;
    toolbarDraggingRef.current = false;
    setToolbarPos((p) => {
      if (p) {
        try {
          localStorage.setItem(TOOLBAR_POS_KEY, JSON.stringify(p));
        } catch {
          /* storage unavailable — position just won't persist */
        }
      }
      return p;
    });
  };

  // Load a question into the live per-part state so the canvases and results
  // panel reflect a fresh exercise (or a resumed/forced one).
  const loadQuestion = (q: Question) => {
    const n = Math.max(1, q.params?.parts?.length ?? 0);
    setQuestion(q);
    initPartState(n);
    // Every part's canvas is mounted simultaneously (only hidden via CSS for
    // non-active parts), so this also wipes any stale ink left over from a
    // DIFFERENT question that happened to reuse the same part-label keys.
    canvasRefs.current.forEach((cv) => {
      if (cv) cv.clear();
    });
  };

  // Once a question's canvases are mounted, auto-fit a grid on the
  // draw-the-graph part to the exercise's reference window, so the student
  // draws directly over where the graph lives (no manual centering).
  useEffect(() => {
    if (!question) return;
    const parts = (question.params?.parts ?? []) as { label: string; want?: string }[];
    const graph = question.params?.graph as
      | { x_min?: number; x_max?: number; y_min?: number; y_max?: number }
      | undefined;
    if (!graph || typeof graph.x_min !== "number") return;
    parts.forEach((p, i) => {
      if (p.want === "draw") {
        canvasRefs.current[i]?.fitGridToWindow(graph.x_min!, graph.x_max!, graph.y_min!, graph.y_max!);
      }
    });
  }, [question]);

  const generateQuestion = async (cfg: SessionConfig): Promise<Question> => {
    const { question_type, variant } =
      cfg.questionType === "any" ? {} : splitTypeValue(cfg.questionType);
    return api.generate(
      cfg.topic === "complex" ? cfg.mode : "templates",
      cfg.difficulty,
      cfg.topic,
      question_type,
      variant
    );
  };

  const newQuestion = async () => {
    setError("");
    setBusy(true);
    setPracticingFormula(null);
    try {
      const cfg: SessionConfig = { mode, topic, questionType, difficulty };
      const q = await generateQuestion(cfg);
      loadQuestion(q);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate");
    } finally {
      setBusy(false);
    }
  };

  // Update the config dropdowns — they only take effect when the student
  // presses "New question" (no auto-regeneration while selecting).
  const changeTopic = (nextTopic: string) => {
    if (nextTopic === topic) return;
    setTopic(nextTopic);
    setQuestionType("any");
  };

  const changeQuestionType = (nextType: string) => {
    if (nextType === questionType) return;
    setQuestionType(nextType);
  };

  const changeDifficulty = (next: string) => setDifficulty(next);
  const changeMode = (next: string) => setMode(next);

  const clearPractice = () => {
    setQuestion(null);
    initPartState(0);
    activeCanvas()?.clear();
    setPracticingFormula(null);
  };

  const uploadImage = () => fileRef.current?.click();

  const exitReview = () => {
    setReviewMode(false);
    setQuestion(null);
    initPartState(0);
    activeCanvas()?.clear();
    router.replace("/practice");
  };

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      activeCanvas()?.loadImage(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  // Runs the actual grade call + marks/sounds, given the FINAL resolved lines
  // (i.e. after any ambiguity has been confirmed/rejected by the student).
  const finalizeCheck = async (det: DetectResult, resolvedLines: string[], resolvedLatex: string[]) => {
    if (!question) return;
    const finalDet: DetectResult = { ...det, lines: resolvedLines, lines_latex: resolvedLatex };
    setBusy(true);
    try {
      const work = resolvedLines.length ? resolvedLines.join("\n") : undefined;
      setWorkText(work ?? null);
      setWorkLatex(resolvedLatex.length ? resolvedLatex : null);
      setDetectResult(finalDet);
      setDetected(finalDet.raw_text || resolvedLines[resolvedLines.length - 1] || "(nothing detected)");
      const answer = finalDet.raw_text || resolvedLines[resolvedLines.length - 1] || "";
      const strokes = activeCanvas()?.getStrokes() ?? null;
      const strokesThumb = activeCanvas()?.getStrokesThumb() ?? null;
      const strokesToSend =
        strokes && JSON.stringify(strokes).length <= 500_000 ? strokes : null;
      const res = await api.grade(
        question.id, answer, work, finalDet.lines_boxes, currentPart ?? undefined, hintLevel,
        strokesToSend, strokesThumb,
      );
      setResult(res);
      const nowDone = res.correct && res.all_complete;
      if (nowDone) {
        setExerciseDone(true);
      } else if (res.correct && currentPart && partLabels.length > 1) {
        setPartIndex((i) => Math.min(i + 1, partLabels.length - 1));
      }
      if (res.explanation) setExplanation(res.explanation);
      if (question.topic === "functions" && res.graph) {
        const thumb = activeCanvas()?.getInkSnapshot();
        if (thumb) {
          api.gradeGraph(question.id, thumb).then((gg) => setGraphGrade(gg)).catch(() => {});
        }
      }
      const map = activeCanvas()?.getExportMap();
      const nextMarks =
        map && finalDet.lines_boxes?.length ? buildMarks(finalDet, res, map, debug) : null;
      setMarks(nextMarks);
      if (map && finalDet.lines_boxes?.length && !reviewMode) {
        const snaps = activeCanvas()?.getLineSnapshots(finalDet.lines_boxes);
        if (snaps?.some(Boolean)) {
          setLinePops(
            snaps.map((s: LineSnapshot | null, i: number) =>
              s ? (
                <image
                  key={`pop-${i}`}
                  href={s.href}
                  x={s.x}
                  y={s.y}
                  width={s.w}
                  height={s.h}
                  className="line-grow"
                  style={{ animationDelay: `${i * MARK_STAGGER_MS}ms` }}
                />
              ) : null
            )
          );
        }
      } else {
        setLinePops(null);
      }
      const newStreak = updateStreak(res.correct);
      setStreak(newStreak);

      // Play the grade sounds in sync with the progressive reveal. When the answer is
      // correct (SymPy-verified), EVERY line celebrates with a rising ding — the
      // intermediate verdicts may not match real handwriting, so the pitch must not
      // depend on them. When wrong: correct lines ding (rising from 0), only the
      // first wrong line thuds, and a final victory ping lands on the stamp.
      const events = nextMarks ? markEvents(finalDet, res) : [];
      if (events.length) {
        if (res.correct) {
          events.forEach((_, i) => {
            setTimeout(() => playMarkSound(true, Math.max(newStreak - 1, 0) + i), i * MARK_STAGGER_MS);
          });
          setTimeout(
            () => playMarkSound(true, Math.max(newStreak - 1, 0) + events.length),
            events.length * MARK_STAGGER_MS
          );
        } else {
          let correctSeen = 0;
          let thudPlayed = false;
          events.forEach((e, i) => {
            const delay = i * MARK_STAGGER_MS;
            if (e.correct) {
              setTimeout(() => playMarkSound(true, correctSeen), delay);
              correctSeen += 1;
            } else if (!thudPlayed) {
              thudPlayed = true;
              setTimeout(() => playMarkSound(false, 0), delay);
            }
          });
        }
      } else {
        playGradeSound(res.correct);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Check failed");
    } finally {
      setBusy(false);
    }
  };

  const check = async () => {
    if (!question) {
      setError("Generate a question first.");
      return;
    }
    setError("");
    setResult(null);
    setExplanation(null);
    setGraphGrade(null);
    setMarks(null);
    setLinePops(null);
    setBusy(true);

    // A "draw the graph" part has no numeric answer — checking it runs the
    // graph-drawing check (gradeGraph) on the ink instead of OCR grading.
    const partsArr = (question.params?.parts ?? []) as { label: string; want?: string }[];
    const activeMeta = currentPart ? partsArr.find((p) => p.label === currentPart) : undefined;
    if (activeMeta?.want === "draw") {
      const thumb = activeCanvas()?.getInkSnapshot();
      if (!thumb) {
        setError("Draw the graph on the page first.");
        setBusy(false);
        return;
      }
      try {
        const gg = await api.gradeGraph(question.id, thumb);
        setGraphGrade(gg);
        setResult({
          correct: true,
          reason: "graph",
          expected: "",
          attempt_id: "",
          part: currentPart ?? undefined,
          all_complete: true,
        } as GradeResult);
        setExerciseDone(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Graph check failed");
      } finally {
        setBusy(false);
      }
      return;
    }

    try {
      const answer = typed.trim();
      if (answer) {
        // Typed answers skip OCR entirely, so there's nothing to disambiguate.
        const finalDet = { lines: [], lines_latex: [], raw_text: answer } as unknown as DetectResult;
        setBusy(false);
        await finalizeCheck(finalDet, [], []);
        return;
      }
      const ink = activeCanvas()?.getImageBase64();
      if (!ink) {
        setError("Write an answer on the page, upload an image, or type one.");
        setBusy(false);
        return;
      }
      const det = await api.detect(ink);
      setDetectResult(det);
      if (!det.raw_text && !det.lines?.length) {
        setError("Could not read the handwriting. Try writing larger or clearer.");
        setBusy(false);
        return;
      }

      const queue: AmbiguousLine[] = [];
      (det.lines ?? []).forEach((text, i) => {
        const alts = det.lines_alt?.[i] ?? [];
        if (!alts.length) return;
        const altLatex = det.lines_alt_latex?.[i] ?? [];
        queue.push({
          index: i,
          primary: { text, latex: det.lines_latex?.[i] },
          candidates: alts.map((t, j) => ({ text: t, latex: altLatex[j] })),
        });
      });

      if (queue.length) {
        pendingDetectRef.current = det;
        setAmbiguityResolved({});
        setAmbiguityQueue(queue);
        setBusy(false);
        return;
      }

      setBusy(false);
      await finalizeCheck(det, det.lines ?? [], det.lines_latex ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Check failed");
      setBusy(false);
    }
  };

  const resolveAmbiguity = (pick: DisambiguationCandidate | null) => {
    if (!ambiguityQueue || !ambiguityQueue.length) return;
    const [current, ...rest] = ambiguityQueue;
    const resolved = { ...ambiguityResolved };
    if (pick) resolved[current.index] = pick;
    if (rest.length) {
      setAmbiguityResolved(resolved);
      setAmbiguityQueue(rest);
      return;
    }
    // Queue exhausted — build the final lines using every resolution (falling
    // back to the OCR's original reading for lines the student confirmed as-is).
    const det = pendingDetectRef.current;
    pendingDetectRef.current = null;
    setAmbiguityQueue(null);
    setAmbiguityResolved({});
    if (!det) return;
    const lines = (det.lines ?? []).map((t, i) => resolved[i]?.text ?? t);
    const latex = (det.lines_latex ?? []).map((t, i) => resolved[i]?.latex ?? t);
    finalizeCheck(det, lines, latex);
  };

  const writeLineAgain = () => {
    if (!ambiguityQueue || !ambiguityQueue.length) return;
    const [current, ...rest] = ambiguityQueue;
    const det = pendingDetectRef.current;
    const box = det?.lines_boxes?.[current.index];
    if (box) activeCanvas()?.eraseRegion(box);
    pendingDetectRef.current = null;
    setAmbiguityQueue(null);
    setAmbiguityResolved({});
    markDirty();
    setError("Redraw that line, then check your work again.");
  };

  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);
  const [savedFlash, setSavedFlash] = useState<string | null>(null);
  const [resumeWriting, setResumeWriting] = useState<(DetectResult | null)[]>([]);
  // Vector strokes to restore into per-part canvases once they mount (resume +
  // review). Loaded in an effect so canvasRefs are populated after re-render.
  const [pendingStrokes, setPendingStrokes] = useState<(StrokeDoc | null)[] | null>(null);

  useEffect(() => {
    if (!pendingStrokes) return;
    pendingStrokes.forEach((doc, i) => {
      const c = canvasRefs.current[i];
      if (c && doc) c.loadStrokes(doc);
    });
    setPendingStrokes(null);
  }, [pendingStrokes]);

  useEffect(() => {
    if (!reviewMode && !question) {
      api.myProgress().then(setSessions).catch(() => {});
    }
  }, [reviewMode, question]);

  const saveProgressNow = async () => {
    if (!question) {
      setError("Generate a question first.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      let ty = typed.trim();
      let wt = workText;
      let boxes = detectResult?.lines_boxes ?? null;
      if (!ty && !wt) {
        const ink = activeCanvas()?.getImageBase64();
        if (ink) {
          const det = await api.detect(ink);
          setDetectResult(det);
          setDetected(det.raw_text || "(nothing detected)");
          wt = det.lines?.length ? det.lines.join("\n") : null;
          boxes = det.lines_boxes ?? null;
          setWorkText(wt);
          setWorkLatex(det.lines_latex?.length ? det.lines_latex : null);
        }
      }
      const strokes = activeCanvas()?.getStrokes() ?? null;
      const strokesThumb = activeCanvas()?.getStrokesThumb() ?? null;
      const strokesToSend =
        strokes && JSON.stringify(strokes).length <= 500_000 ? strokes : null;
      const summary = await api.saveProgress(
        question.id, currentPart ?? undefined,
        ty || undefined, wt ?? undefined, boxes ?? undefined,
        strokesToSend, strokesThumb,
      );
      setSavedFlash(`Saved (${summary.parts_done}/${summary.parts_total} parts)`);
      setTimeout(() => setSavedFlash(null), 3000);
      api.myProgress().then(setSessions).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const deleteSession = async (id: string) => {
    try {
      await api.deleteProgress(id);
      setSessions((s) => (s ? s.filter((x) => x.id !== id) : s));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const loadSession = async (id: string) => {
    setBusy(true);
    try {
      const d = await api.progress(id);
      const labels = Object.keys(d.parts);
      if (!d.question) throw new Error("Question missing from saved progress");
      setQuestion(d.question);
      initPartState(labels.length);
      setReviewMode(false);
      setResumeWriting(Array(labels.length).fill(null));
      const strokesArr: (StrokeDoc | null)[] = Array(labels.length).fill(null);
      let firstUndone = labels.length - 1;
      const allDone = labels.length > 0;
      labels.forEach((lab, i) => {
        const st = d.parts[lab];
        if (!st) return;
        setAt(setTypedByPart, i, st.typed ?? "");
        setAt(setWorkTextByPart, i, st.work_text ?? null);
        setAt(setWorkLatexByPart, i, null);
        if (st.strokes) strokesArr[i] = st.strokes;
        if (st.lines_boxes?.length) {
          const det = {
            lines: (st.work_text ?? "").split("\n").filter(Boolean),
            lines_boxes: st.lines_boxes,
          } as DetectResult;
          setAt(setResumeWriting, i, det);
        }
        if (st.correct) {
          setAt(setResultByPart, i, {
            correct: true, reason: "saved", expected: "", attempt_id: "",
          } as GradeResult);
        } else if (firstUndone === labels.length - 1) {
          firstUndone = i;
        }
      });
      const done = allDone && labels.every((lab) => d.parts[lab]?.correct);
      setExerciseDone(done);
      setPartIndex(firstUndone);
      setPendingStrokes(strokesArr);

      // Keep the config dropdowns in sync so "New question" generates in the
      // resumed exercise's topic/type/difficulty.
      setMode("templates");
      setTopic(d.question.topic);
      setQuestionType(d.question.question_type);
      setDifficulty(d.question.difficulty);
      router.replace("/practice");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resume");
    } finally {
      setBusy(false);
    }
  };

  const showExplanation = async () => {
    if (!question) return;
    setBusy(true);
    try {
      const exp = await api.explain(question.id, detected ?? undefined, workText ?? undefined);
      setExplanation(exp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Explain failed");
    } finally {
      setBusy(false);
    }
  };

  // Hint: reveals one more solution step per click instead of the whole
  // explanation at once. Fetches the explanation lazily on first click.
  const showHint = async () => {
    if (!explanation) {
      await showExplanation();
      setHintLevel(1);
      return;
    }
    setHintLevel((n) => Math.min(n + 1, explanation.steps?.length ?? n + 1));
  };

  const replayReview = async () => {
    if (!question) return;
    setBusy(true);
    try {
      const q = await api.replay(question.id);
      setReviewMode(false);
      setQuestion(q);
      initPartState(q.params?.parts?.length ?? 0);
      activeCanvas()?.clear();
      router.replace("/practice");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to replay exercise");
    } finally {
      setBusy(false);
    }
  };

  const bannerShown = reviewMode || !!practicingFormula;

  return (
    <AuthGuard>
      <div className="relative">
        {reviewMode && (
          <div className="fixed top-[76px] left-1/2 -translate-x-1/2 z-30 flex items-center gap-3 bg-[#23272e]/90 text-slate-100 text-sm rounded-lg px-3 py-2 shadow-lg pointer-events-auto">
            <span>Reviewing a past attempt — your writing is restored, draw on it or start fresh.</span>
            <button
              onClick={replayReview}
              disabled={busy}
              className="px-2 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-xs font-medium"
            >
              Do the same exercise again
            </button>
            <button
              onClick={exitReview}
              className="px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-xs font-medium"
            >
              Exit review
            </button>
          </div>
        )}
        {practicingFormula && !reviewMode && (
          <div className="fixed top-[76px] left-1/2 -translate-x-1/2 z-30 flex items-center gap-3 bg-[#23272e]/90 text-slate-100 text-sm rounded-lg px-3 py-2 shadow-lg pointer-events-auto">
            <span>
              Practicing: <span className="font-semibold capitalize">{practicingFormula.name}</span>
            </span>
            <button
              onClick={() => setPracticingFormula(null)}
              className="px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-xs font-medium"
            >
              Dismiss
            </button>
          </div>
        )}
        <style>{MARKS_STYLE}</style>

        {partLabels.length > 0 && (
          <div
            className={`fixed left-1/2 -translate-x-1/2 z-30 flex items-center gap-1 bg-white/95 backdrop-blur border border-[#e4e2db] rounded-lg shadow-md px-2 py-1.5 pointer-events-auto ${
              bannerShown ? "top-[124px]" : "top-[76px]"
            }`}
          >
            <span className="text-xs text-[#8a857b] pr-1">Part</span>
            {partLabels.map((lab, i) => {
              const done = !!resultByPart[i]?.correct;
              return (
                <button
                  key={lab}
                  onClick={() => setActivePart(i)}
                  disabled={busy}
                  className={`px-2.5 py-1 stylus:px-3 stylus:py-2 rounded text-sm font-semibold transition-colors ${
                    i === partIndex
                      ? "bg-[#23272e] text-white"
                      : done
                      ? "bg-emerald-100 text-emerald-800"
                      : "text-[#6b6558] hover:bg-[#faf9f6]"
                  }`}
                >
                  {done ? "✓ " : ""}
                  {lab}
                </button>
              );
            })}
          </div>
        )}

        {partLabels.length > 0 ? (
          partLabels.map((lab, i) => (
            <div key={lab} className={i === partIndex ? "" : "hidden"}>
              <Canvas
                ref={(el) => {
                  canvasRefs.current[i] = el;
                }}
                fullscreen
                zoom={zoom}
                onChange={markDirty}
                onZoomChange={onCanvasZoomChange}
                overlay={
                  marksByPart[i]?.length || linePopsByPart[i]?.length || (i === partIndex && ambiguityQueue?.length) ? (
                    <>
                      {linePopsByPart[i]}
                      {marksByPart[i]}
                      {i === partIndex && renderAmbiguityCard()}
                    </>
                  ) : undefined
                }
              />
            </div>
          ))
        ) : (
          <Canvas
            ref={(el) => {
              canvasRefs.current[0] = el;
            }}
            fullscreen
            zoom={zoom}
            onChange={markDirty}
            onZoomChange={onCanvasZoomChange}
            overlay={
              marks?.length || linePops?.length || ambiguityQueue?.length ? (
                <>
                  {linePops}
                  {marks}
                  {renderAmbiguityCard()}
                </>
              ) : undefined
            }
          />
        )}

        {/* Question bar: Find <prompt> ................ Question N of 20  Skip */}
        <div className="fixed inset-x-0 top-0 z-10 min-h-[68px] bg-white border-b border-[#e4e2db] flex items-center justify-between gap-3 pl-7 pr-6 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))]">
          <div className="flex items-center gap-2.5 min-w-0">
            {question ? (
              <div className="flex items-baseline gap-2.5 min-w-0">
                <span className="font-medium text-[#23272e] text-base shrink-0">Find</span>
                {question.prompt_latex ? (
                  <MathText text={`\\(${question.prompt_latex}\\)`} className="text-[#23272e]" />
                ) : (
                  <span className="font-medium text-[#23272e]">{question.prompt}</span>
                )}
              </div>
            ) : (
              <span className="text-[#8a857b] text-sm">
                Pick a topic &amp; difficulty, then press New question.
              </span>
            )}
          </div>

          <div className="flex items-center gap-3.5 shrink-0">
            {!reviewMode && (
              <>
                <select
                  value={topic}
                  onChange={(e) => changeTopic(e.target.value)}
                  className="px-2 py-1.5 rounded-md border border-[#dddad1] text-[12.5px] text-[#3f3c35] bg-white"
                  title="Topic"
                >
                  <option value="complex">Complex numbers</option>
                  <option value="limit">Limits</option>
                  <option value="integral">Integrals</option>
                  <option value="probability">Probability</option>
                  <option value="functions">Functions</option>
                </select>
                <select
                  value={questionType}
                  onChange={(e) => changeQuestionType(e.target.value)}
                  className="px-2 py-1.5 rounded-md border border-[#dddad1] text-[12.5px] text-[#3f3c35] bg-white"
                  title="Question type"
                >
                  <option value="any">Any type</option>
                  {TYPE_OPTIONS[topic].map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
                <select
                  value={difficulty}
                  onChange={(e) => changeDifficulty(e.target.value)}
                  className="px-2 py-1.5 rounded-md border border-[#dddad1] text-[12.5px] text-[#3f3c35] bg-white"
                  title="Difficulty"
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
                {topic === "complex" && (
                  <select
                    value={mode}
                    onChange={(e) => changeMode(e.target.value)}
                    className="px-2 py-1.5 rounded-md border border-[#dddad1] text-[12.5px] text-[#3f3c35] bg-white"
                    title="Generation mode"
                  >
                    <option value="templates">Templates</option>
                    <option value="gemini">Gemini</option>
                  </select>
                )}
              </>
            )}
            {streak > 0 && (
              <span
                className="px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 text-xs font-semibold whitespace-nowrap"
                title="Consecutive correct answers"
              >
                🔥 {streak}
              </span>
            )}
            {savedFlash && (
              <span className="text-xs text-emerald-700 font-semibold bg-emerald-50 px-2 py-1 rounded border border-emerald-200">
                {savedFlash}
              </span>
            )}
            {sessions && sessions.length > 0 && !reviewMode && (
              <details className="relative">
                <summary className="px-[13px] py-2 stylus:px-4 stylus:py-3 rounded-[7px] border border-[#dddad1] text-[12.5px] font-medium text-[#6b6558] hover:bg-[#faf9f6] cursor-pointer select-none list-none [&::-webkit-details-marker]:hidden">
                  Saved ({sessions.length})
                </summary>
                <div className="absolute right-0 top-full mt-1.5 w-72 max-h-64 overflow-y-auto bg-white border border-[#e4e2db] rounded-lg shadow-lg p-2 space-y-1.5 z-40">
                  {sessions.map((s) => (
                    <div
                      key={s.id}
                      className="flex items-center justify-between gap-2 rounded-md border border-[#e4e2db] bg-[#faf9f6] p-2"
                    >
                      <div className="min-w-0">
                        <div className="text-xs font-medium text-[#23272e] truncate">
                          {(s.question?.prompt ?? "").split("\n")[0]}
                        </div>
                        <div className="text-[11px] text-[#8a857b]">
                          {s.question?.question_type.replace("_", " ")} · {s.parts_done}/{s.parts_total} parts
                          {s.status === "completed" ? " · done" : ""}
                        </div>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <button
                          onClick={() => loadSession(s.id)}
                          disabled={busy}
                          className="px-2.5 py-1 rounded-md bg-[#23272e] text-white text-xs font-medium hover:bg-[#31363f]"
                        >
                          Resume
                        </button>
                        <button
                          onClick={() => deleteSession(s.id)}
                          disabled={busy}
                          className="px-2 py-1 rounded-md border border-[#dddad1] text-xs text-[#8a857b] hover:bg-white"
                          title="Delete saved progress"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            )}
            <button
              onClick={saveProgressNow}
              disabled={busy || !question}
              className="px-[13px] py-2 stylus:px-4 stylus:py-3 rounded-[7px] border border-[#dddad1] text-[12.5px] font-medium text-[#6b6558] hover:bg-[#faf9f6] disabled:opacity-50"
              title="Save progress for later"
            >
              Save
            </button>
            <button
              onClick={newQuestion}
              disabled={busy}
              className="px-[15px] py-2 stylus:px-5 stylus:py-3 rounded-[7px] bg-[#23272e] text-white text-[12.5px] font-semibold hover:bg-[#31363f] disabled:opacity-50"
              title="Generate a new question"
            >
              {busy ? "Working..." : "New question"}
            </button>
          </div>
        </div>

        {error && (
          <div className="fixed top-[76px] left-1/2 -translate-x-1/2 z-20 pointer-events-none">
            <p className="pointer-events-auto bg-red-50 border border-red-200 text-red-700 text-xs rounded-md px-3 py-1.5 shadow-md">
              {error}
            </p>
          </div>
        )}

        {/* Right-side results / explanation panel */}
        <div className="fixed right-3 bottom-24 z-10 w-[calc(100vw-1.5rem)] sm:w-96 max-h-[55vh] overflow-y-auto pointer-events-auto space-y-3">
          {result && (
            <div
              className={`rounded-lg p-3 border shadow-md ${
                result.correct ? "bg-emerald-50/95 border-emerald-200" : "bg-red-50/95 border-red-200"
              }`}
            >
              <div className="font-bold text-[#23272e]">
                {exerciseDone
                  ? "Exercise complete!"
                  : result.correct
                  ? `Part ${result.part ?? ""} correct`
                  : "Incorrect"}
              </div>
              {exerciseDone && (
                <button
                  onClick={newQuestion}
                  disabled={busy}
                  className="mt-2 w-full px-3 py-2 rounded-lg bg-[#23272e] text-white text-xs font-semibold hover:bg-[#31363f] disabled:opacity-50"
                >
                  {busy ? "Working..." : "Next question →"}
                </button>
              )}
              {partLabels.length > 0 && (
                <div className="mt-1 flex items-center gap-1 text-xs">
                  {partLabels.map((lab, i) => (
                    <span
                      key={lab}
                      className={`px-1.5 py-0.5 rounded ${
                        i < partIndex || (exerciseDone && i === partIndex)
                          ? "bg-emerald-600 text-white"
                          : i === partIndex
                          ? "bg-[#23272e] text-white"
                          : "bg-[#e4e2db] text-[#8a857b]"
                      }`}
                    >
                      {lab}
                    </span>
                  ))}
                </div>
              )}
              {result.parts?.length ? (
                <div className="mt-2 space-y-1 text-sm">
                  {result.parts.map((pv) => (
                    <div
                      key={pv.label}
                      className={`rounded px-2 py-1 ${
                        pv.correct ? "bg-emerald-100/80 text-emerald-900" : "bg-red-100/80 text-red-900"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">
                          {pv.correct ? "✓" : "✗"} Part {pv.label}
                        </span>
                        <span className="text-xs">
                          {pv.given ? `you: ${pv.given} · ` : ""}
                          {pv.correct ? "" : `expected ${pv.expected}`}
                          {!pv.correct && !pv.given ? "(unanswered)" : ""}
                        </span>
                      </div>
                      {pv.note && (
                        <div className="mt-0.5 text-xs text-emerald-800/90">{pv.note}</div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                !result.correct && (
                  <div className="mt-1 text-sm text-[#3f3c35]">
                    Expected: <span className="font-medium">{result.expected}</span>
                  </div>
                )
              )}
              <div className="mt-1 text-xs text-[#8a857b]">Reason: {result.reason}</div>
              {!result.correct &&
                result.step_check?.first_error_line != null &&
                (() => {
                  const fumbled = result.step_check!.line_results.find(
                    (l) => l.line === result.step_check!.first_error_line
                  )?.formula;
                  if (!fumbled) return null;
                  return (
                    <Link
                      href={`/practice?formula=${fumbled}`}
                      className="mt-2 inline-block px-2.5 py-1 rounded-md bg-[#23272e] text-white text-xs font-medium hover:bg-[#31363f]"
                    >
                      Practice: {fumbled.replaceAll("_", " ")}
                    </Link>
                  );
                })()}
              {result.graph && (
                <div className="mt-3 border-t border-[#e4e2db] pt-2">
                  <div className="text-xs font-medium text-[#8a857b] uppercase mb-1">
                    Reference graph — compare with your drawing
                  </div>
                  <FunctionGraph graph={result.graph} />
                  {result.graph_check && (
                    <div className="mt-2 text-xs">
                      <div className="text-[#8a857b]">Labels your drawing includes:</div>
                      <div className="mt-0.5 flex flex-wrap gap-x-2">
                        {result.graph_check.items.map((it) => (
                          <span
                            key={it.label}
                            className={it.found ? "text-emerald-700 font-semibold" : "text-[#8a857b] opacity-60"}
                          >
                            {it.label} {it.found ? "✓" : "·"}
                          </span>
                        ))}
                      </div>
                      {result.graph_check.found < result.graph_check.total && (
                        <div className="mt-1 text-[#8a857b] text-[11px]">
                          Missing labels aren't counted wrong — add them and redraw to match the
                          reference curve.
                        </div>
                      )}
                    </div>
                  )}
                  {graphGrade && !graphGrade.error && (
                    <div className="mt-3 border-t border-[#e4e2db] pt-2">
                      <div className="text-xs font-medium text-[#8a857b] uppercase mb-1">
                        Graph Drawing Assessment
                      </div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className={`text-lg font-bold ${graphGrade.score! >= 80 ? "text-emerald-700" : graphGrade.score! >= 60 ? "text-amber-600" : "text-red-600"}`}>
                          {graphGrade.score}/100
                        </span>
                        <div className="flex gap-1.5 text-xs">
                          {graphGrade.curve_correct !== undefined && (
                            <span className={graphGrade.curve_correct ? "text-emerald-700" : "text-red-600"}>
                              Curve {graphGrade.curve_correct ? "✓" : "✗"}
                            </span>
                          )}
                          {graphGrade.asymptotes_correct !== undefined && (
                            <span className={graphGrade.asymptotes_correct ? "text-emerald-700" : "text-red-600"}>
                              Asymptotes {graphGrade.asymptotes_correct ? "✓" : "✗"}
                            </span>
                          )}
                          {graphGrade.tangent_correct !== null && graphGrade.tangent_correct !== undefined && (
                            <span className={graphGrade.tangent_correct ? "text-emerald-700" : "text-red-600"}>
                              Tangent {graphGrade.tangent_correct ? "✓" : "✗"}
                            </span>
                          )}
                          {graphGrade.points_correct !== undefined && (
                            <span className={graphGrade.points_correct ? "text-emerald-700" : "text-red-600"}>
                              Points {graphGrade.points_correct ? "✓" : "✗"}
                            </span>
                          )}
                        </div>
                      </div>
                      {graphGrade.feedback && (
                        <p className="text-xs text-[#3f3c35] mb-1">{graphGrade.feedback}</p>
                      )}
                      {graphGrade.suggestions && graphGrade.suggestions.length > 0 && (
                        <ul className="text-[11px] text-[#8a857b] list-disc list-inside space-y-0.5">
                          {graphGrade.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      )}
                    </div>
                  )}
                  {graphGrade?.error === "rate_limited" && (
                    <div className="mt-2 text-[11px] text-[#8a857b]">
                      Graph assessment unavailable (rate limited).
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {(explanation || workText) && (
            <div className="bg-white/90 backdrop-blur border border-[#e4e2db] rounded-lg shadow-md p-3">
              {workText && workText.split("\n").length > 1 && (
                <div className="mb-2 pb-2 border-b border-[#e4e2db]">
                  <div className="text-xs text-[#8a857b] uppercase font-medium">Your work</div>
                  <div className="mt-1 text-sm space-y-0.5">
                    {workText.split("\n").map((line, idx) => {
                      const lineNo = idx + 1;
                      const errLine = result?.step_check?.first_error_line;
                      const isError = errLine === lineNo;
                      const latex = workLatex?.[idx];
                      const lineRes = result?.step_check?.line_results.find((r) => r.line === lineNo);
                      const formulaName = lineRes?.formula ? lineRes.formula.replaceAll("_", " ") : null;
                      return (
                        <div key={idx} className={isError ? "text-red-700 font-semibold" : "text-[#6b6558]"}>
                          {isError ? "→ " : ""}
                          {latex ? <MathText text={`\\(${latex}\\)`} /> : <MathText text={line} />}
                          {isError && formulaName && (
                            <span className="ml-1 text-xs opacity-70">({formulaName})</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {explanation && (
                <div className="text-sm leading-relaxed">
                  {explanation.steps?.length ? (
                    <div className="space-y-1.5 mb-2">
                      <div className="text-xs font-medium text-[#8a857b] uppercase">Solution</div>
                      {explanation.steps.slice(0, hintLevel || explanation.steps.length).map((s) => (
                        <div key={s.step_order} className="flex gap-1.5">
                          <span className="font-medium text-[#23272e] whitespace-nowrap">Step {s.step_order}:</span>
                          <MathText text={s.detail} className="text-[#3f3c35]" />
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {(!hintLevel || hintLevel >= (explanation.steps?.length ?? 0)) && (
                    <MathText text={explanation.content} className="whitespace-pre-wrap" />
                  )}
                  {explanation.work_check?.content && (
                    <div className="mt-3 border-t border-[#e4e2db] pt-2">
                      <div className="text-xs font-medium text-[#8a857b] uppercase">Your work check</div>
                      <MathText text={explanation.work_check.content} className="mt-1 whitespace-pre-wrap" />
                    </div>
                  )}
                  {explanation.graph && (
                    <div className="mt-3 border-t border-[#e4e2db] pt-2">
                      <div className="text-xs font-medium text-[#8a857b] uppercase mb-1">
                        Reference graph
                      </div>
                      <FunctionGraph graph={explanation.graph} />
                      {explanation.graph_check && (
                        <div className="mt-2 text-xs">
                          <div className="text-[#8a857b]">Labels your drawing includes:</div>
                          <div className="mt-0.5 flex flex-wrap gap-x-2">
                            {explanation.graph_check.items.map((it) => (
                              <span
                                key={it.label}
                                className={it.found ? "text-emerald-700 font-semibold" : "text-[#8a857b] opacity-60"}
                              >
                                {it.label} {it.found ? "✓" : "·"}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Toolbar — docked bottom-center (respecting the safe area) by default,
            drag the grip to move it anywhere. Buttons pick up bigger touch
            targets under `stylus:` (pointer: coarse — finger/pen tablets)
            without bloating them for precise mouse users, and the row wraps
            instead of overflowing off-screen on a narrower portrait tablet. */}
        <div
          ref={toolbarRef}
          className="fixed z-10 pointer-events-auto flex items-center gap-1.5 bg-white rounded-xl shadow-[0px_2px_8px_0px_rgba(0,0,0,0.08)] p-2"
          style={
            toolbarPos
              ? { left: toolbarPos.x, top: toolbarPos.y }
              : { left: "50%", bottom: "max(24px, env(safe-area-inset-bottom))", transform: "translateX(-50%)" }
          }
        >
          <div
            onPointerDown={startToolbarDrag}
            onPointerMove={moveToolbarDrag}
            onPointerUp={endToolbarDrag}
            onPointerCancel={endToolbarDrag}
            title="Drag to move"
            className="self-stretch flex flex-col flex-wrap items-center justify-center gap-[3px] px-1.5 cursor-grab active:cursor-grabbing touch-none"
          >
            {Array.from({ length: 6 }).map((_, i) => (
              <span key={i} className="w-1 h-1 rounded-full bg-[#c7c2b6]" />
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-center gap-2 max-w-[85vw]">
            <div className="flex items-center gap-0.5 bg-[#f1f0ec] rounded-[9px] p-[3px]">
              <button
                onClick={() => selectTool("pen")}
                title="Pen (P)"
                className={`px-[14px] py-2 stylus:px-4 stylus:py-3 rounded-[6px] text-[12.5px] font-medium ${
                  tool === "pen"
                    ? "bg-white text-[#23272e] shadow-[0px_1px_2px_0px_rgba(0,0,0,0.08)]"
                    : "text-[#7a756a] font-normal"
                }`}
              >
                Pen
              </button>
              <button
                onClick={() => selectTool("eraser")}
                title="Eraser (E)"
                className={`px-[14px] py-2 stylus:px-4 stylus:py-3 rounded-[6px] text-[12.5px] font-medium ${
                  tool === "eraser"
                    ? "bg-white text-[#23272e] shadow-[0px_1px_2px_0px_rgba(0,0,0,0.08)]"
                    : "text-[#7a756a] font-normal"
                }`}
              >
                Eraser
              </button>
              <button
                onClick={() => selectTool("ruler")}
                title="Straight line / ruler (R)"
                className={`px-[14px] py-2 stylus:px-4 stylus:py-3 rounded-[6px] text-[12.5px] font-medium ${
                  tool === "ruler"
                    ? "bg-white text-[#23272e] shadow-[0px_1px_2px_0px_rgba(0,0,0,0.08)]"
                    : "text-[#7a756a] font-normal"
                }`}
              >
                Line
              </button>
              <button
                onClick={() => selectTool("curve")}
                title="Curve — drag to bend a smooth line (C)"
                className={`px-[14px] py-2 stylus:px-4 stylus:py-3 rounded-[6px] text-[12.5px] font-medium ${
                  tool === "curve"
                    ? "bg-white text-[#23272e] shadow-[0px_1px_2px_0px_rgba(0,0,0,0.08)]"
                    : "text-[#7a756a] font-normal"
                }`}
              >
                Curve
              </button>
              <button
                onClick={() => selectTool("ellipse")}
                title="Ellipse — drag corner-to-corner (O)"
                className={`px-[14px] py-2 stylus:px-4 stylus:py-3 rounded-[6px] text-[12.5px] font-medium ${
                  tool === "ellipse"
                    ? "bg-white text-[#23272e] shadow-[0px_1px_2px_0px_rgba(0,0,0,0.08)]"
                    : "text-[#7a756a] font-normal"
                }`}
              >
                Ellipse
              </button>
            </div>
            <button
              onClick={selectAxes}
              title="Coordinate axes (G): select to spawn, tap the page to move the origin, use scale/Δ to resize"
              className={`px-[13px] py-2.5 stylus:px-4 stylus:py-3 rounded-[7px] border text-[12.5px] font-medium ${
                tool === "axes" && gridOn
                  ? "border-[#23272e] bg-[#23272e] text-white"
                  : gridOn
                  ? "border-[#bfdbfe] bg-[#eff6ff] text-[#1d4ed8]"
                  : "border-[#e4e2db] text-[#6b6558] hover:bg-[#faf9f6]"
              }`}
            >
              {tool === "axes" && gridOn ? "Axes ✓" : "Axes"}
            </button>
            {tool === "axes" && gridOn && (
              <>
                <div className="flex items-center gap-1.5 rounded-[7px] border border-[#e4e2db] px-2 py-1.5 text-[12px] text-[#6b6558]" title="Zoom: pixels per unit">
                  <span>scale</span>
                  <input
                    type="number"
                    min={10}
                    max={200}
                    step={5}
                    value={gridScale}
                    onChange={(e) => changeGridScale(Number(e.target.value))}
                    className="w-12 border border-[#e4e2db] rounded-[5px] px-1 py-0.5 text-center text-[#23272e]"
                    aria-label="Grid scale (px per unit)"
                  />
                </div>
                <div className="flex items-center gap-1.5 rounded-[7px] border border-[#e4e2db] px-2 py-1.5 text-[12px] text-[#6b6558]">
                  <span>Δx</span>
                  <input
                    type="number"
                    min={0.5}
                    max={50}
                    step={0.5}
                    value={gridStep.x}
                    onChange={(e) => changeGridStep("x", Number(e.target.value))}
                    className="w-11 border border-[#e4e2db] rounded-[5px] px-1 py-0.5 text-center text-[#23272e]"
                    aria-label="Grid x step"
                  />
                  <span>Δy</span>
                  <input
                    type="number"
                    min={0.5}
                    max={50}
                    step={0.5}
                    value={gridStep.y}
                    onChange={(e) => changeGridStep("y", Number(e.target.value))}
                    className="w-11 border border-[#e4e2db] rounded-[5px] px-1 py-0.5 text-center text-[#23272e]"
                    aria-label="Grid y step"
                  />
                </div>
                {question?.params?.graph && (
                  <button
                    onClick={() => {
                      const g = question.params.graph as {
                        x_min?: number;
                        x_max?: number;
                        y_min?: number;
                        y_max?: number;
                      };
                      if (typeof g.x_min === "number") {
                        activeCanvas()?.fitGridToWindow(g.x_min!, g.x_max!, g.y_min!, g.y_max!);
                      }
                    }}
                    className="px-[13px] py-2.5 stylus:px-4 stylus:py-3 rounded-[7px] border border-[#e4e2db] text-[12.5px] font-medium text-[#6b6558] hover:bg-[#faf9f6]"
                    title="Re-fit the grid to the exercise's reference window"
                  >
                    Fit
                  </button>
                )}
              </>
            )}
            <button
              onClick={undo}
              disabled={!canUndo}
              className="px-[13px] py-2.5 stylus:px-4 stylus:py-3 rounded-[7px] border border-[#e4e2db] text-[12.5px] font-medium text-[#6b6558] hover:bg-[#faf9f6] disabled:opacity-40"
            >
              Undo
            </button>
            <button
              onClick={redo}
              disabled={!canRedo}
              className="px-[13px] py-2.5 stylus:px-4 stylus:py-3 rounded-[7px] border border-[#e4e2db] text-[12.5px] font-medium text-[#6b6558] hover:bg-[#faf9f6] disabled:opacity-40"
            >
              Redo
            </button>
            <div className="w-px h-[26px] bg-[#e4e2db]" />
            <button
              onClick={() => {
                activeCanvas()?.clear();
                setDetected(null);
                setWorkText(null);
                setDetectResult(null);
                setMarks(null);
                setLinePops(null);
                markDirty();
              }}
              className="px-[15px] py-2.5 stylus:px-4 stylus:py-3 rounded-[7px] border border-[#e4e2db] text-[12.5px] font-medium text-[#9a9488] hover:bg-[#faf9f6]"
            >
              Clear
            </button>
            <button
              onClick={showHint}
              disabled={busy || !question}
              className="px-[15px] py-2.5 stylus:px-4 stylus:py-3 rounded-[7px] border border-[#dddad1] text-[12.5px] font-medium text-[#6b6558] hover:bg-[#faf9f6] disabled:opacity-40"
            >
              {explanation?.steps?.length && hintLevel >= explanation.steps.length ? "All hints shown" : "Hint"}
            </button>
            <button
              onClick={uploadImage}
              className="px-[15px] py-2.5 stylus:px-4 stylus:py-3 rounded-[7px] border border-[#dddad1] text-[12.5px] font-medium text-[#6b6558] hover:bg-[#faf9f6]"
            >
              Upload
            </button>
            <div className="flex items-center rounded-[7px] border border-[#dddad1] overflow-hidden text-xs">
              <button onClick={zoomOut} className="px-2 py-2.5 stylus:px-3 stylus:py-3 hover:bg-[#faf9f6] text-[#6b6558]" title="Zoom out">
                −
              </button>
              <span className="px-1.5 min-w-[2.5rem] text-center text-[#8a857b]">{Math.round(zoom * 100)}%</span>
              <button onClick={zoomIn} className="px-2 py-2.5 stylus:px-3 stylus:py-3 hover:bg-[#faf9f6] text-[#6b6558]" title="Zoom in">
                +
              </button>
            </div>
            <input
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              placeholder="or type answer"
              className="w-28 px-3 py-2.5 stylus:py-3 border border-[#dddad1] rounded-[7px] text-xs placeholder:text-[#a8a296]"
            />
            <button
              onClick={check}
              disabled={busy}
              className="px-[15px] py-2.5 stylus:px-6 stylus:py-3.5 rounded-[7px] bg-[#23272e] text-white text-[12.5px] font-medium hover:bg-[#31363f] disabled:opacity-50"
            >
              {busy ? "Working..." : "Check my work"}
            </button>
          </div>
        </div>

        {/* Pen/eraser size + debug, tucked into an unobtrusive corner strip */}
        <div className="fixed left-3 top-1/2 -translate-y-1/2 z-10 pointer-events-auto flex flex-col items-center gap-2 bg-white/90 backdrop-blur border border-[#e4e2db] rounded-lg shadow-md p-2">
          <span className="text-[10px] text-[#a8a296]">{tool === "eraser" ? 100 : 30}</span>
          <input
            type="range"
            min={tool === "eraser" ? 10 : 1}
            max={tool === "eraser" ? 100 : 30}
            step={1}
            value={tool === "eraser" ? eraserWidth : penWidth}
            onChange={(e) =>
              tool === "eraser"
                ? selectEraserWidth(Number(e.target.value))
                : selectPenWidth(Number(e.target.value))
            }
            className="w-6 h-24 stylus:w-10 stylus:h-32 accent-[#23272e] [writing-mode:vertical-lr] [direction:rtl] cursor-pointer"
            aria-label="Size"
          />
          <span className="text-[10px] text-[#a8a296]">{tool === "eraser" ? 10 : 1}</span>
          <span className="text-xs font-semibold text-[#6b6558] tabular-nums">
            {tool === "eraser" ? eraserWidth : penWidth}
          </span>
          <div className="w-full border-t border-[#e4e2db] my-1" />
          <button
            onClick={() => setDebug((d) => !d)}
            title="Toggle debug panel"
            className={`w-7 h-7 stylus:w-9 stylus:h-9 rounded text-[10px] font-bold ${
              debug ? "bg-[#23272e] text-white" : "text-[#a8a296] hover:bg-[#faf9f6]"
            }`}
          >
            DBG
          </button>
        </div>

        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onFile} />

        {debug && (
          <div className="fixed left-20 bottom-3 z-10 w-[calc(100vw-6rem)] sm:w-[26rem] max-h-[45vh] overflow-y-auto pointer-events-auto bg-slate-900/95 backdrop-blur text-slate-100 rounded-lg p-3 text-xs space-y-2 shadow-lg">
            <div className="font-semibold text-slate-300">Debug</div>
            <div>
              <span className="text-slate-400">Question:</span> {question?.prompt ?? "none"}
            </div>
            {question && (
              <div>
                <span className="text-slate-400">Question id:</span> {question.id}
                <span className="text-slate-400"> · topic:</span> {question.topic}
                <span className="text-slate-400"> · type:</span> {question.question_type}
                <span className="text-slate-400"> · params:</span> {JSON.stringify(question.params)}
              </div>
            )}
            <div>
              <span className="text-slate-400">Detected:</span>{" "}
              {detectResult ? (
                <>
                  {detectResult.lines.length > 0 && (
                    <div className="mt-1 mb-1 overflow-x-auto">
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="text-slate-400">
                            <th className="pr-2">#</th>
                            <th className="pr-2">verdict</th>
                            <th className="pr-2">conf</th>
                            <th className="pr-2">box</th>
                            <th>text</th>
                          </tr>
                        </thead>
                        <tbody>
                          {detectResult.lines.map((ln, i) => {
                            const lr = result?.step_check?.line_results.find((r) => r.line === i + 1);
                            let verdict = "—";
                            let vc = "text-slate-400";
                            if (lr?.checked) {
                              verdict = lr.correct ? "OK" : "WRONG";
                              vc = lr.correct ? "text-emerald-400" : "text-red-400";
                            } else if (lr?.reason === "given") {
                              verdict = "given";
                            } else if (lr?.reason === "unparsed") {
                              verdict = "unparsed";
                              vc = "text-amber-400";
                            }
                            return (
                              <tr key={i} className="border-t border-slate-700">
                                <td className="pr-2 py-0.5 text-slate-200">{i + 1}</td>
                                <td className={`pr-2 py-0.5 ${vc}`}>{verdict}</td>
                                <td className="pr-2 py-0.5 text-slate-400">
                                  {detectResult.lines_confidence?.[i]?.toFixed(2) ?? "—"}
                                </td>
                                <td className="pr-2 py-0.5 text-slate-400">
                                  {JSON.stringify(detectResult.lines_boxes?.[i] ?? null)}
                                </td>
                                <td className="py-0.5 text-slate-300 whitespace-nowrap">{ln}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <pre className="mt-1 whitespace-pre-wrap break-all">{JSON.stringify(detectResult, null, 2)}</pre>
                </>
              ) : (
                "no detection yet"
              )}
            </div>
            <div>
              <span className="text-slate-400">Grade:</span>{" "}
              {result ? (
                <pre className="mt-1 whitespace-pre-wrap break-all">
                  {JSON.stringify(
                    { correct: result.correct, reason: result.reason, given: result.given, expected: result.expected },
                    null,
                    2
                  )}
                </pre>
              ) : (
                "no grade yet"
              )}
            </div>
          </div>
        )}
      </div>
    </AuthGuard>
  );

  function renderAmbiguityCard() {
    if (!ambiguityQueue || !ambiguityQueue.length) return null;
    const current = ambiguityQueue[0];
    const box = pendingDetectRef.current?.lines_boxes?.[current.index];
    const map = activeCanvas()?.getExportMap();
    if (!box || box.length !== 4 || !map) return null;
    const rect = {
      x1: map.offsetX + box[0] * map.scale,
      y1: map.offsetY + box[1] * map.scale,
      x2: map.offsetX + box[2] * map.scale,
      y2: map.offsetY + box[3] * map.scale,
    };
    return (
      <DisambiguationCard
        lineNumber={current.index + 1}
        box={rect}
        canvasW={map.canvasW}
        primary={current.primary}
        candidates={current.candidates}
        onPick={(i) => resolveAmbiguity(current.candidates[i])}
        onNone={() => resolveAmbiguity(null)}
        onWriteAgain={writeLineAgain}
      />
    );
  }
}
