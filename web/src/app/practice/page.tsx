"use client";

import { ReactNode, Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import AuthGuard from "@/components/AuthGuard";
import Canvas, { CanvasExportMap, CanvasHandle, CanvasTool, FULL_W, LineSnapshot, PEN_WIDTHS } from "@/components/Canvas";
import MathText from "@/components/MathText";
import DisambiguationCard, { DisambiguationCandidate } from "@/components/DisambiguationCard";
import { api, Question, GradeResult, Explanation, DetectResult } from "@/lib/api";
import { getStreak, playGradeSound, playMarkSound, updateStreak } from "@/lib/sounds";

const CURSIVE = "'Segoe Script', 'Comic Sans MS', cursive";

const MARK_STAGGER_MS = 1000;
const SESSION_TOTAL = 20;

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

const TYPE_OPTIONS: Record<string, { value: string; label: string }[]> = {
  complex: [
    { value: "modulus", label: "Modulus" },
    { value: "argument", label: "Argument" },
    { value: "conjugate", label: "Conjugate" },
    { value: "real_part", label: "Real part" },
    { value: "imaginary_part", label: "Imaginary part" },
  ],
  limit: [{ value: "limit", label: "Limit" }],
  integral: [
    { value: "definite_integral", label: "Definite integral" },
    { value: "indefinite_integral", label: "Indefinite integral" },
  ],
  probability: [{ value: "probability", label: "Probability" }],
};

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

function PracticeInner() {
  const canvasRefs = useRef<(CanvasHandle | null)[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const pendingDetectRef = useRef<DetectResult | null>(null);

  const [question, setQuestion] = useState<Question | null>(null);
  const [partIndex, setPartIndex] = useState(0);
  const [exerciseDone, setExerciseDone] = useState(false);

  // Session setup (shown before the canvas). Once started, `sessionActive`
  // drives the "Question N of 20" header + Skip; config stays fixed for the
  // whole session.
  const [sessionActive, setSessionActive] = useState(false);
  const [sessionIndex, setSessionIndex] = useState(1);
  const [sessionCorrect, setSessionCorrect] = useState(0);
  const [sessionDone, setSessionDone] = useState(false);
  const [mode, setMode] = useState("templates");
  const [topic, setTopic] = useState("complex");
  const [questionType, setQuestionType] = useState("any");
  const [difficulty, setDifficulty] = useState("medium");
  const sessionConfigRef = useRef<SessionConfig | null>(null);

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
  const [hintLevel, setHintLevel] = useState(0);
  const [ambiguityQueue, setAmbiguityQueue] = useState<AmbiguousLine[] | null>(null);
  const [ambiguityResolved, setAmbiguityResolved] = useState<Record<number, DisambiguationCandidate>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [debug, setDebug] = useState(false);
  const [tool, setTool] = useState<CanvasTool>("pen");
  const [penWidth, setPenWidth] = useState<number>(PEN_WIDTHS.medium);
  const [eraserWidth, setEraserWidth] = useState<number>(32);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [streak, setStreak] = useState(0);
  const [reviewMode, setReviewMode] = useState(false);
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
        setReviewMode(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load attempt");
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
      } else if (k === "[") {
        if (tool === "pen") selectPenWidth(Math.max(1, penWidth - 1));
        else selectEraserWidth(Math.max(10, eraserWidth - 1));
      } else if (k === "]") {
        if (tool === "pen") selectPenWidth(Math.min(30, penWidth + 1));
        else selectEraserWidth(Math.min(100, eraserWidth + 1));
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tool, penWidth, eraserWidth]);

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

  const generateOne = async (cfg: SessionConfig) => {
    const q = await api.generate(
      cfg.topic === "complex" ? cfg.mode : "templates",
      cfg.difficulty,
      cfg.topic,
      cfg.questionType === "any" ? undefined : cfg.questionType
    );
    setQuestion(q);
    initPartState(q.params?.parts?.length ?? 0);
  };

  const startSession = async () => {
    setError("");
    setBusy(true);
    try {
      const cfg: SessionConfig = { mode, topic, questionType, difficulty };
      sessionConfigRef.current = cfg;
      await generateOne(cfg);
      setSessionIndex(1);
      setSessionCorrect(0);
      setSessionDone(false);
      setSessionActive(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate");
    } finally {
      setBusy(false);
    }
  };

  const advanceSession = async (wasCorrect: boolean) => {
    if (wasCorrect) setSessionCorrect((c) => c + 1);
    if (sessionIndex >= SESSION_TOTAL) {
      setSessionDone(true);
      return;
    }
    setError("");
    activeCanvas()?.clear();
    setBusy(true);
    try {
      await generateOne(sessionConfigRef.current!);
      setSessionIndex((i) => i + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate");
    } finally {
      setBusy(false);
    }
  };

  const skip = () => advanceSession(false);

  const endSession = () => {
    setSessionActive(false);
    setSessionDone(false);
    setQuestion(null);
    initPartState(0);
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
      const res = await api.grade(question.id, answer, work, finalDet.lines_boxes, currentPart ?? undefined);
      setResult(res);
      const nowDone = res.correct && res.all_complete;
      if (nowDone) {
        setExerciseDone(true);
      } else if (res.correct && currentPart && partLabels.length > 1) {
        setPartIndex((i) => Math.min(i + 1, partLabels.length - 1));
      }
      if (res.explanation) setExplanation(res.explanation);
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
      if (nowDone && sessionActive) advanceSession(true);

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
    setMarks(null);
    setLinePops(null);
    setBusy(true);
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

  const showSetup = !reviewMode && !sessionActive;

  if (showSetup) {
    return (
      <AuthGuard>
        <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-slate-50 px-4">
          <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
            <div>
              <h1 className="text-xl font-bold text-slate-900">Start a practice session</h1>
              <p className="mt-1 text-sm text-slate-500">
                {SESSION_TOTAL} questions, handwritten and graded instantly.
              </p>
            </div>
            <div className="space-y-3">
              <label className="block">
                <span className="text-xs font-medium text-slate-600">Topic</span>
                <select
                  value={topic}
                  onChange={(e) => {
                    setTopic(e.target.value);
                    setQuestionType("any");
                  }}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                >
                  <option value="complex">Complex numbers</option>
                  <option value="limit">Limits</option>
                  <option value="integral">Integrals</option>
                  <option value="probability">Probability</option>
                </select>
              </label>
              <label className="block">
                <span className="text-xs font-medium text-slate-600">Question type</span>
                <select
                  value={questionType}
                  onChange={(e) => setQuestionType(e.target.value)}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                >
                  <option value="any">Any type</option>
                  {TYPE_OPTIONS[topic].map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-xs font-medium text-slate-600">Difficulty</span>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </label>
              {topic === "complex" && (
                <label className="block">
                  <span className="text-xs font-medium text-slate-600">Generation mode</span>
                  <select
                    value={mode}
                    onChange={(e) => setMode(e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                  >
                    <option value="templates">Templates</option>
                    <option value="gemini">Gemini</option>
                  </select>
                </label>
              )}
            </div>
            {error && <p className="text-xs text-red-600">{error}</p>}
            <button
              onClick={startSession}
              disabled={busy}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-900 text-white text-sm font-semibold hover:bg-slate-700 disabled:opacity-50"
            >
              {busy ? "Starting..." : `Start session (${SESSION_TOTAL} questions)`}
            </button>
          </div>
        </div>
      </AuthGuard>
    );
  }

  if (sessionDone) {
    return (
      <AuthGuard>
        <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-slate-50 px-4">
          <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-sm p-6 text-center space-y-4">
            <h1 className="text-xl font-bold text-slate-900">Session complete!</h1>
            <p className="text-4xl font-extrabold text-emerald-600">
              {sessionCorrect} / {SESSION_TOTAL}
            </p>
            <p className="text-sm text-slate-500">correct on the first check</p>
            <div className="flex gap-2">
              <button
                onClick={startSession}
                disabled={busy}
                className="flex-1 px-4 py-2.5 rounded-lg bg-slate-900 text-white text-sm font-semibold hover:bg-slate-700 disabled:opacity-50"
              >
                Start another session
              </button>
              <button
                onClick={endSession}
                className="px-4 py-2.5 rounded-lg border border-slate-300 text-sm font-medium hover:bg-slate-50"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <div className="relative">
        {reviewMode && (
          <div className="fixed top-3 left-1/2 -translate-x-1/2 z-30 flex items-center gap-3 bg-slate-900/90 text-slate-100 text-sm rounded-lg px-3 py-2 shadow-lg pointer-events-auto">
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
        <style>{MARKS_STYLE}</style>

        {partLabels.length > 0 && (
          <div
            className={`fixed left-1/2 -translate-x-1/2 z-30 flex items-center gap-1 bg-white/95 backdrop-blur border border-slate-200 rounded-lg shadow-md px-2 py-1.5 pointer-events-auto ${
              reviewMode ? "top-16" : "top-3"
            }`}
          >
            <span className="text-xs text-slate-400 pr-1">Part</span>
            {partLabels.map((lab, i) => {
              const done = !!resultByPart[i]?.correct;
              return (
                <button
                  key={lab}
                  onClick={() => setActivePart(i)}
                  disabled={busy}
                  className={`px-2.5 py-1 stylus:px-3 stylus:py-2 rounded text-sm font-semibold transition-colors ${
                    i === partIndex
                      ? "bg-slate-900 text-white"
                      : done
                      ? "bg-emerald-100 text-emerald-800"
                      : "text-slate-600 hover:bg-slate-100"
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

        {/* Top bar: Find <prompt> ................ Question N of 20  Skip */}
        <div className="fixed inset-x-0 top-0 z-10 flex items-start justify-between gap-3 px-3 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))] pointer-events-none">
          <div className="pointer-events-auto max-w-2xl bg-white/95 backdrop-blur border border-slate-200 rounded-lg shadow-md px-4 py-2.5">
            {question ? (
              <div className="flex items-baseline gap-2 text-lg text-slate-900">
                <span className="font-semibold text-slate-500 text-sm uppercase tracking-wide">Find</span>
                {question.prompt_latex ? (
                  <MathText text={`\\(${question.prompt_latex}\\)`} />
                ) : (
                  <span className="font-semibold">{question.prompt}</span>
                )}
              </div>
            ) : (
              <span className="text-slate-400 text-sm">Loading question…</span>
            )}
          </div>

          <div className="pointer-events-auto flex items-center gap-2 bg-white/95 backdrop-blur border border-slate-200 rounded-lg shadow-md px-3 py-2.5">
            {sessionActive && (
              <span className="text-sm text-slate-500 whitespace-nowrap">
                Question {sessionIndex} of {SESSION_TOTAL}
              </span>
            )}
            {streak > 0 && (
              <span
                className="px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 text-xs font-semibold whitespace-nowrap"
                title="Consecutive correct answers"
              >
                🔥 {streak}
              </span>
            )}
            <button
              onClick={skip}
              disabled={busy}
              className="px-3 py-1.5 stylus:px-4 stylus:py-2.5 rounded-md border border-slate-300 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
            >
              Skip
            </button>
          </div>
        </div>

        {error && (
          <div className="fixed top-16 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
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
              <div className="font-bold text-slate-900">
                {exerciseDone
                  ? "Exercise complete!"
                  : result.correct
                  ? `Part ${result.part ?? ""} correct`
                  : "Incorrect"}
              </div>
              {partLabels.length > 0 && (
                <div className="mt-1 flex items-center gap-1 text-xs">
                  {partLabels.map((lab, i) => (
                    <span
                      key={lab}
                      className={`px-1.5 py-0.5 rounded ${
                        i < partIndex || (exerciseDone && i === partIndex)
                          ? "bg-emerald-600 text-white"
                          : i === partIndex
                          ? "bg-slate-900 text-white"
                          : "bg-slate-200 text-slate-500"
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
                      className={`flex items-center justify-between rounded px-2 py-1 ${
                        pv.correct ? "bg-emerald-100/80 text-emerald-900" : "bg-red-100/80 text-red-900"
                      }`}
                    >
                      <span className="font-semibold">
                        {pv.correct ? "✓" : "✗"} Part {pv.label}
                      </span>
                      <span className="text-xs">
                        {pv.given ? `you: ${pv.given} · ` : ""}
                        {pv.correct ? "" : `expected ${pv.expected}`}
                        {!pv.correct && !pv.given ? "(unanswered)" : ""}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                !result.correct && (
                  <div className="mt-1 text-sm text-slate-700">
                    Expected: <span className="font-medium">{result.expected}</span>
                  </div>
                )
              )}
              <div className="mt-1 text-xs text-slate-500">Reason: {result.reason}</div>
            </div>
          )}

          {(explanation || workText) && (
            <div className="bg-white/90 backdrop-blur border border-slate-200 rounded-lg shadow-md p-3">
              {workText && workText.split("\n").length > 1 && (
                <div className="mb-2 pb-2 border-b border-slate-200">
                  <div className="text-xs text-slate-500 uppercase font-medium">Your work</div>
                  <div className="mt-1 text-sm space-y-0.5">
                    {workText.split("\n").map((line, idx) => {
                      const lineNo = idx + 1;
                      const errLine = result?.step_check?.first_error_line;
                      const isError = errLine === lineNo;
                      const latex = workLatex?.[idx];
                      const lineRes = result?.step_check?.line_results.find((r) => r.line === lineNo);
                      const formulaName = lineRes?.formula ? lineRes.formula.replaceAll("_", " ") : null;
                      return (
                        <div key={idx} className={isError ? "text-red-700 font-semibold" : "text-slate-600"}>
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
                      <div className="text-xs font-medium text-slate-500 uppercase">Solution</div>
                      {explanation.steps.slice(0, hintLevel || explanation.steps.length).map((s) => (
                        <div key={s.step_order} className="flex gap-1.5">
                          <span className="font-medium text-slate-900 whitespace-nowrap">Step {s.step_order}:</span>
                          <MathText text={s.detail} className="text-slate-700" />
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {(!hintLevel || hintLevel >= (explanation.steps?.length ?? 0)) && (
                    <MathText text={explanation.content} className="whitespace-pre-wrap" />
                  )}
                  {explanation.work_check?.content && (
                    <div className="mt-3 border-t border-slate-200 pt-2">
                      <div className="text-xs font-medium text-slate-500 uppercase">Your work check</div>
                      <MathText text={explanation.work_check.content} className="mt-1 whitespace-pre-wrap" />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Bottom pill toolbar. Buttons pick up bigger touch targets under
            `stylus:` (pointer: coarse — finger/pen tablets) without bloating
            them for precise mouse users, and the pill wraps instead of
            overflowing off-screen on a narrower portrait tablet. Bottom
            padding respects the safe area for iPad landscape/PWA use. */}
        <div className="fixed inset-x-0 bottom-[max(0.75rem,env(safe-area-inset-bottom))] z-10 flex justify-center pointer-events-none px-3">
          <div className="pointer-events-auto flex flex-wrap items-center justify-center gap-1 max-w-[95vw] bg-white/95 backdrop-blur border border-slate-200 rounded-[1.75rem] shadow-lg px-2 py-2">
            <button
              onClick={() => selectTool("pen")}
              title="Pen (P)"
              className={`px-3 py-2 stylus:px-4 stylus:py-3 rounded-full text-sm font-medium ${
                tool === "pen" ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              Pen
            </button>
            <button
              onClick={() => selectTool("eraser")}
              title="Eraser (E)"
              className={`px-3 py-2 stylus:px-4 stylus:py-3 rounded-full text-sm font-medium ${
                tool === "eraser" ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              Eraser
            </button>
            <div className="w-px h-6 bg-slate-200 mx-1" />
            <button
              onClick={undo}
              disabled={!canUndo}
              className="px-3 py-2 stylus:px-4 stylus:py-3 rounded-full text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40"
            >
              Undo
            </button>
            <button
              onClick={redo}
              disabled={!canRedo}
              className="px-3 py-2 stylus:px-4 stylus:py-3 rounded-full text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40"
            >
              Redo
            </button>
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
              className="px-3 py-2 stylus:px-4 stylus:py-3 rounded-full text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Clear
            </button>
            <div className="w-px h-6 bg-slate-200 mx-1" />
            <button
              onClick={showHint}
              disabled={busy || !question}
              className="px-3 py-2 stylus:px-4 stylus:py-3 rounded-full text-sm font-medium text-amber-700 hover:bg-amber-50 disabled:opacity-40"
            >
              {explanation?.steps?.length && hintLevel >= explanation.steps.length ? "All hints shown" : "Hint"}
            </button>
            <button
              onClick={uploadImage}
              className="px-3 py-2 stylus:px-4 stylus:py-3 rounded-full text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Upload
            </button>
            <div className="flex items-center rounded-full border border-slate-200 overflow-hidden text-xs ml-1">
              <button onClick={zoomOut} className="px-2 py-2 stylus:px-3 stylus:py-3 hover:bg-slate-50" title="Zoom out">
                −
              </button>
              <span className="px-1.5 min-w-[2.5rem] text-center text-slate-500">{Math.round(zoom * 100)}%</span>
              <button onClick={zoomIn} className="px-2 py-2 stylus:px-3 stylus:py-3 hover:bg-slate-50" title="Zoom in">
                +
              </button>
            </div>
            <input
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              placeholder="or type answer"
              className="ml-1 w-28 px-2 py-2 stylus:py-3 border border-slate-200 rounded-full text-xs"
            />
            <button
              onClick={check}
              disabled={busy}
              className="ml-1 px-5 py-2.5 stylus:px-6 stylus:py-3.5 rounded-full bg-slate-900 text-white text-sm font-semibold hover:bg-slate-700 disabled:opacity-50"
            >
              {busy ? "Working..." : "Check my work"}
            </button>
          </div>
        </div>

        {/* Pen/eraser size + debug, tucked into an unobtrusive corner strip */}
        <div className="fixed left-3 top-1/2 -translate-y-1/2 z-10 pointer-events-auto flex flex-col items-center gap-2 bg-white/90 backdrop-blur border border-slate-200 rounded-lg shadow-md p-2">
          <span className="text-[10px] text-slate-400">{tool === "pen" ? 30 : 100}</span>
          <input
            type="range"
            min={tool === "pen" ? 1 : 10}
            max={tool === "pen" ? 30 : 100}
            step={1}
            value={tool === "pen" ? penWidth : eraserWidth}
            onChange={(e) =>
              tool === "pen" ? selectPenWidth(Number(e.target.value)) : selectEraserWidth(Number(e.target.value))
            }
            className="w-6 h-24 stylus:w-10 stylus:h-32 accent-slate-900 [writing-mode:vertical-lr] [direction:rtl] cursor-pointer"
            aria-label="Size"
          />
          <span className="text-[10px] text-slate-400">{tool === "pen" ? 1 : 10}</span>
          <span className="text-xs font-semibold text-slate-700 tabular-nums">
            {tool === "pen" ? penWidth : eraserWidth}
          </span>
          <div className="w-full border-t border-slate-200 my-1" />
          <button
            onClick={() => setDebug((d) => !d)}
            title="Toggle debug panel"
            className={`w-7 h-7 stylus:w-9 stylus:h-9 rounded text-[10px] font-bold ${
              debug ? "bg-slate-900 text-white" : "text-slate-400 hover:bg-slate-100"
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
