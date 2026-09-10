"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Canvas, { CanvasHandle, CanvasTool, PEN_WIDTHS } from "@/components/Canvas";
import MathText from "@/components/MathText";
import MathKeypad from "@/components/MathKeypad";
import { api, SandboxGradeResult, SandboxSolveResult, TemplateSummary } from "@/lib/api";

type FocusableField = HTMLInputElement | HTMLTextAreaElement;

// A field value typed by the admin is sent as JSON when it parses as one
// (numbers, "[1,2,3]" vectors, "{"x0":0}" initial-condition dicts) so
// structured params round-trip exactly; anything else (a math expression
// like "sqrt(2)" or a bare name like "x") goes through as a raw string for
// the backend's own tolerant parser to interpret.
function toSendValue(raw: string): unknown {
  const trimmed = raw.trim();
  if (trimmed === "") return "";
  try {
    return JSON.parse(trimmed);
  } catch {
    return raw;
  }
}

function stringifyParam(v: unknown): string {
  if (typeof v === "string") return v;
  if (v === null || v === undefined) return "";
  return JSON.stringify(v);
}

const TOPBAR_H = 48;

export default function AdminSandbox({ summary, onExit }: { summary: TemplateSummary | null; onExit?: () => void }) {
  const topics = summary?.topics ?? [];
  const [topic, setTopic] = useState(topics[0]?.topic ?? "complex");
  const questionTypes = topics.find((t) => t.topic === topic)?.question_types ?? [];
  const [questionType, setQuestionType] = useState(questionTypes[0]?.question_type ?? "");
  const [difficulty, setDifficulty] = useState("medium");

  const [paramKeys, setParamKeys] = useState<string[]>([]);
  const [params, setParams] = useState<Record<string, string>>({});
  const [newKey, setNewKey] = useState("");

  const [lines, setLines] = useState("");

  const canvasRef = useRef<CanvasHandle | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [tool, setToolState] = useState<CanvasTool>("pen");
  const [zoom, setZoom] = useState(1);
  const [detectBusy, setDetectBusy] = useState(false);
  const [toolsVisible, setToolsVisible] = useState(true);

  const [sampleBusy, setSampleBusy] = useState(false);
  const [solveBusy, setSolveBusy] = useState(false);
  const [gradeBusy, setGradeBusy] = useState(false);
  const [error, setError] = useState("");
  const [solveResult, setSolveResult] = useState<SandboxSolveResult | null>(null);
  const [gradeResult, setGradeResult] = useState<SandboxGradeResult | null>(null);
  const [prompt, setPrompt] = useState<{ text: string | null; latex: string | null } | null>(null);

  const activeEl = useRef<FocusableField | null>(null);

  const qtOptionsFor = (tp: string) => topics.find((t) => t.topic === tp)?.question_types ?? [];

  const onTopicChange = (tp: string) => {
    setTopic(tp);
    const first = qtOptionsFor(tp)[0]?.question_type ?? "";
    setQuestionType(first);
    setParamKeys([]);
    setParams({});
    setSolveResult(null);
    setGradeResult(null);
    setPrompt(null);
  };

  const loadSample = async () => {
    if (!topic || !questionType) return;
    setSampleBusy(true);
    setError("");
    try {
      const sample = await api.sandboxSample(topic, questionType, difficulty);
      const keys = Object.keys(sample.params);
      setParamKeys(keys);
      setParams(Object.fromEntries(keys.map((k) => [k, stringifyParam(sample.params[k])])));
      setPrompt({ text: sample.prompt, latex: sample.prompt_latex });
      setSolveResult(null);
      setGradeResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sample");
    } finally {
      setSampleBusy(false);
    }
  };

  const addField = () => {
    const key = newKey.trim();
    if (!key || paramKeys.includes(key)) return;
    setParamKeys((ks) => [...ks, key]);
    setParams((p) => ({ ...p, [key]: "" }));
    setNewKey("");
  };

  const removeField = (key: string) => {
    setParamKeys((ks) => ks.filter((k) => k !== key));
    setParams((p) => {
      const next = { ...p };
      delete next[key];
      return next;
    });
  };

  const sendParams = useMemo(
    () => () => Object.fromEntries(paramKeys.map((k) => [k, toSendValue(params[k] ?? "")])),
    [paramKeys, params]
  );

  const runSolve = async () => {
    setSolveBusy(true);
    setError("");
    setSolveResult(null);
    try {
      const res = await api.sandboxSolve(topic, questionType, sendParams());
      setSolveResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Solve failed");
    } finally {
      setSolveBusy(false);
    }
  };

  const runGrade = async () => {
    setGradeBusy(true);
    setError("");
    setGradeResult(null);
    try {
      const res = await api.sandboxGrade(topic, questionType, sendParams(), lines);
      setGradeResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Grade failed");
    } finally {
      setGradeBusy(false);
    }
  };

  // --- handwriting canvas: pen input + pasted/uploaded images + OCR into
  // the "Test grading" lines box. The canvas here is fullscreen (same as
  // the student practice page) rather than a small embedded box, so the
  // admin gets the same amount of drawing room a student has; the sandbox's
  // own controls live in a toggleable side panel instead of pushing the
  // canvas into a small column.
  const selectTool = (t: CanvasTool) => {
    setToolState(t);
    canvasRef.current?.setTool(t);
  };

  const onFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      canvasRef.current?.loadImage(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  // Canvas's own paste listener only runs when fullscreen is driven by its
  // own internal layout; it's simplest to keep our own listener here too so
  // it keeps working regardless of Canvas's internal wiring.
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA)$/.test(target.tagName)) return;
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (!item.type.startsWith("image/")) continue;
        const file = item.getAsFile();
        if (file) onFile(file);
        break;
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

  const recognizeHandwriting = async () => {
    const image = canvasRef.current?.getImageBase64();
    if (!image) {
      setError("Draw or paste something on the canvas first.");
      return;
    }
    setDetectBusy(true);
    setError("");
    try {
      const det = await api.detect(image);
      setLines(det.lines.join("\n"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Handwriting recognition failed");
    } finally {
      setDetectBusy(false);
    }
  };

  const zoomIn = () => setZoom((z) => Math.min(3, +(z + 0.1).toFixed(2)));
  const zoomOut = () => setZoom((z) => Math.max(0.3, +(z - 0.1).toFixed(2)));

  // --- keypad wiring: insert/move/clear act on whichever field was last
  // focused (see MathKeypad's own comment for why buttons don't steal focus).
  const setFieldValue = (field: string, value: string) => {
    if (field === "lines") {
      setLines(value);
    } else if (field.startsWith("param:")) {
      const key = field.slice(6);
      setParams((p) => ({ ...p, [key]: value }));
    }
  };

  const insertToken = (token: string, caretBack = 0) => {
    const el = activeEl.current;
    const field = el?.dataset.field;
    if (!el || !field) return;
    const value = el.value;
    const start = el.selectionStart ?? value.length;
    const end = el.selectionEnd ?? value.length;
    let next: string;
    let newPos: number;
    if (token === "") {
      if (start !== end) {
        next = value.slice(0, start) + value.slice(end);
        newPos = start;
      } else if (start > 0) {
        next = value.slice(0, start - 1) + value.slice(end);
        newPos = start - 1;
      } else {
        next = value;
        newPos = 0;
      }
    } else {
      next = value.slice(0, start) + token + value.slice(end);
      newPos = start + token.length - caretBack;
    }
    setFieldValue(field, next);
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(newPos, newPos);
    });
  };

  const moveCaret = (dir: -1 | 1) => {
    const el = activeEl.current;
    if (!el) return;
    const pos = Math.max(0, Math.min(el.value.length, (el.selectionStart ?? 0) + dir));
    el.focus();
    el.setSelectionRange(pos, pos);
  };

  const clearActiveField = () => {
    const el = activeEl.current;
    const field = el?.dataset.field;
    if (!el || !field) return;
    setFieldValue(field, "");
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(0, 0);
    });
  };

  const fieldClass =
    "w-full px-2.5 py-1.5 border border-slate-300 rounded-md text-sm font-mono focus:outline-none focus:ring-2 focus:ring-slate-400";
  const toolBtn = (active: boolean) =>
    `px-2.5 py-1 rounded-md text-xs font-medium capitalize ${
      active ? "bg-slate-900 text-white" : "border border-slate-300 text-slate-600 hover:bg-slate-50 bg-white"
    }`;

  return (
    <div className="fixed inset-0 z-40 bg-[#faf9f6] flex flex-col">
      <div
        className="shrink-0 flex items-center justify-between px-4 border-b border-slate-200 bg-white"
        style={{ height: TOPBAR_H }}
      >
        <div className="flex items-center gap-3">
          <button onClick={onExit} className="text-sm text-slate-500 hover:text-slate-900">
            ← Admin
          </button>
          <span className="text-sm font-semibold text-slate-900">Sandbox</span>
          {questionType && (
            <span className="text-xs text-slate-400">
              {topic.replace("_", " ")} / {questionType.replace("_", " ")}
            </span>
          )}
        </div>
        <button
          onClick={() => setToolsVisible((v) => !v)}
          className="px-3 py-1.5 rounded-md text-xs font-medium border border-slate-300 text-slate-700 hover:bg-slate-50 bg-white"
        >
          {toolsVisible ? "Hide tools" : "Show tools"}
        </button>
      </div>

      <div className="relative flex-1 min-h-0">
        <Canvas
          ref={canvasRef}
          fullscreen
          topOffset={TOPBAR_H}
          zoom={zoom}
          onZoomChange={setZoom}
          onToolAutoSwitch={setToolState}
        />

        {/* Floating drawing toolbar, always visible regardless of the side panel. */}
        <div className="fixed left-1/2 -translate-x-1/2 bottom-4 z-10 flex flex-wrap items-center justify-center gap-1.5 bg-white rounded-xl shadow-lg border border-slate-200 p-2 max-w-[calc(100vw-2rem)]">
          {(["pen", "eraser", "select"] as CanvasTool[]).map((t) => (
            <button key={t} onClick={() => selectTool(t)} className={toolBtn(tool === t)}>
              {t}
            </button>
          ))}
          <div className="w-px h-5 bg-slate-200 mx-1" />
          {Object.entries(PEN_WIDTHS).map(([name, w]) => (
            <button
              key={name}
              onClick={() => canvasRef.current?.setPenWidth(w)}
              title={`${name} pen`}
              className="w-7 h-7 rounded-md border border-slate-300 bg-white text-slate-500 hover:bg-slate-50 flex items-center justify-center"
            >
              <span className="rounded-full bg-slate-700" style={{ width: Math.min(w, 12), height: Math.min(w, 12) }} />
            </button>
          ))}
          <div className="w-px h-5 bg-slate-200 mx-1" />
          <button onClick={() => canvasRef.current?.undo()} className={toolBtn(false)}>
            Undo
          </button>
          <button onClick={() => canvasRef.current?.redo()} className={toolBtn(false)}>
            Redo
          </button>
          <button onClick={() => canvasRef.current?.clear()} className={toolBtn(false)}>
            Clear
          </button>
          <button onClick={() => fileInputRef.current?.click()} className={toolBtn(false)}>
            Upload image
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onFile(file);
              e.target.value = "";
            }}
          />
          <div className="w-px h-5 bg-slate-200 mx-1" />
          <button onClick={zoomOut} className="w-7 h-7 rounded-md border border-slate-300 bg-white text-slate-500 hover:bg-slate-50">
            −
          </button>
          <span className="text-xs text-slate-500 w-10 text-center">{Math.round(zoom * 100)}%</span>
          <button onClick={zoomIn} className="w-7 h-7 rounded-md border border-slate-300 bg-white text-slate-500 hover:bg-slate-50">
            +
          </button>
          <div className="w-px h-5 bg-slate-200 mx-1" />
          <button
            onClick={recognizeHandwriting}
            disabled={detectBusy}
            className="px-3 py-1 rounded-md text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {detectBusy ? "Reading…" : "Recognize → fill lines"}
          </button>
        </div>

        {toolsVisible && (
          <div
            className="fixed right-0 z-20 w-full sm:w-[400px] bg-white border-l border-slate-200 shadow-xl overflow-y-auto"
            style={{ top: TOPBAR_H, bottom: 0 }}
          >
            <div className="p-4 space-y-4">
              {error && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</p>
              )}

              <section>
                <h2 className="text-sm font-semibold text-slate-900 mb-2">Choose a template</h2>
                <div className="flex flex-wrap gap-2">
                  <select
                    value={topic}
                    onChange={(e) => onTopicChange(e.target.value)}
                    className="px-2.5 py-1.5 border border-slate-300 rounded-md text-sm capitalize"
                  >
                    {topics.map((t) => (
                      <option key={t.topic} value={t.topic}>
                        {t.topic.replace("_", " ")}
                      </option>
                    ))}
                  </select>
                  <select
                    value={questionType}
                    onChange={(e) => setQuestionType(e.target.value)}
                    className="px-2.5 py-1.5 border border-slate-300 rounded-md text-sm capitalize"
                  >
                    {questionTypes.map((qt) => (
                      <option key={qt.question_type} value={qt.question_type}>
                        {qt.question_type.replace("_", " ")}
                      </option>
                    ))}
                  </select>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    className="px-2.5 py-1.5 border border-slate-300 rounded-md text-sm capitalize"
                  >
                    {["easy", "medium", "hard"].map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={loadSample}
                    disabled={sampleBusy || !questionType}
                    className="px-3 py-1.5 rounded-md text-sm font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                  >
                    {sampleBusy ? "Loading…" : "Load sample params"}
                  </button>
                </div>
                {prompt?.latex && (
                  <div className="mt-3 text-sm text-slate-700 bg-slate-50 rounded p-2 overflow-x-auto">
                    <MathText text={`\\(${prompt.latex}\\)`} />
                  </div>
                )}
              </section>

              <section className="pt-4 border-t border-slate-100">
                <h2 className="text-sm font-semibold text-slate-900 mb-2">
                  Params <span className="text-slate-400 font-normal">— tap a field, then use the keypad</span>
                </h2>
                <div className="space-y-2">
                  {paramKeys.map((key) => (
                    <div key={key} className="flex items-center gap-2">
                      <code className="w-20 shrink-0 text-xs text-slate-500 truncate" title={key}>
                        {key}
                      </code>
                      <input
                        data-field={`param:${key}`}
                        value={params[key] ?? ""}
                        onFocus={(e) => (activeEl.current = e.target)}
                        onChange={(e) => setParams((p) => ({ ...p, [key]: e.target.value }))}
                        className={fieldClass}
                      />
                      <button
                        onClick={() => removeField(key)}
                        className="w-7 h-7 shrink-0 rounded border border-slate-200 text-slate-400 hover:bg-slate-50 hover:text-red-500"
                        title="Remove field"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                  {paramKeys.length === 0 && (
                    <p className="text-sm text-slate-400">
                      No params yet — load a sample, or add a field manually below.
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100">
                  <input
                    value={newKey}
                    onChange={(e) => setNewKey(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addField()}
                    placeholder="param name (e.g. a)"
                    className="px-2.5 py-1.5 border border-slate-300 rounded-md text-sm w-32"
                  />
                  <button
                    onClick={addField}
                    className="px-3 py-1.5 rounded-md text-sm font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50"
                  >
                    + Add field
                  </button>
                </div>
                <button
                  onClick={runSolve}
                  disabled={solveBusy || !questionType}
                  className="mt-4 px-4 py-2 rounded-md text-sm font-semibold bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {solveBusy ? "Solving…" : "Solve"}
                </button>
              </section>

              <MathKeypad onKey={insertToken} onMove={moveCaret} onClear={clearActiveField} />

              {solveResult && (
                <section className="pt-4 border-t border-slate-100">
                  <h2 className="text-sm font-semibold text-slate-900 mb-2">Solver output</h2>
                  <div className="text-sm text-slate-700 bg-slate-50 rounded p-2 mb-3 overflow-x-auto">
                    <span className="text-slate-400 mr-1">Answer:</span>
                    <MathText text={`\\(${solveResult.answer_latex}\\)`} className="inline" />
                    <span className="ml-2 text-slate-400">({solveResult.answer_exact})</span>
                  </div>
                  {solveResult.formula_tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {solveResult.formula_tags.map((t) => (
                        <code key={t} className="px-1.5 py-0.5 rounded bg-slate-100 text-[11px]">
                          {t}
                        </code>
                      ))}
                    </div>
                  )}
                  {solveResult.checkpoints.length > 0 && (
                    <div className="mb-3">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1">
                        Checkpoints
                      </div>
                      <table className="w-full text-xs">
                        <tbody>
                          {solveResult.checkpoints.map((cp, i) => (
                            <tr key={i} className="border-t border-slate-100">
                              <td className="py-1 pr-2 text-slate-500">{cp.label}</td>
                              <td className="py-1 pr-2 font-mono text-slate-800">{cp.value}</td>
                              <td className="py-1 text-slate-400">{cp.formula ?? ""}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <div className="space-y-2">
                    {solveResult.steps.map((s, i) => (
                      <div key={i} className="text-sm">
                        <div className="font-medium text-slate-800">{s.title}</div>
                        <div className="text-slate-600 overflow-x-auto">
                          <MathText text={s.detail} />
                        </div>
                      </div>
                    ))}
                  </div>
                  <details className="mt-3 pt-2 border-t border-slate-100">
                    <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-800">
                      Params actually used (after parsing)
                    </summary>
                    <pre className="mt-1 text-[11px] bg-slate-50 rounded p-2 overflow-x-auto">
                      {JSON.stringify(solveResult.params_used, null, 2)}
                    </pre>
                  </details>
                </section>
              )}

              <section className="pt-4 border-t border-slate-100">
                <h2 className="text-sm font-semibold text-slate-900 mb-2">
                  Test grading{" "}
                  <span className="text-slate-400 font-normal">
                    — write on the canvas and hit &quot;Recognize&quot;, or type lines directly
                  </span>
                </h2>
                <textarea
                  data-field="lines"
                  value={lines}
                  onFocus={(e) => (activeEl.current = e.target)}
                  onChange={(e) => setLines(e.target.value)}
                  rows={5}
                  placeholder={"z = 12-9i, a=12, b=-9\n|z| = sqrt(12^2 + (-9)^2)\n|z| = sqrt(225) = 15"}
                  className={`${fieldClass} font-mono`}
                />
                <button
                  onClick={runGrade}
                  disabled={gradeBusy || !questionType || !lines.trim()}
                  className="mt-3 px-4 py-2 rounded-md text-sm font-semibold bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {gradeBusy ? "Grading…" : "Grade"}
                </button>

                {gradeResult && (
                  <div className="mt-4 space-y-4">
                    <div>
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1">
                        Line-by-line
                      </div>
                      <div className="space-y-1">
                        {gradeResult.step_check.line_results.map((r, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs font-mono">
                            <span className="w-4 shrink-0 text-slate-400">{r.line}</span>
                            <span
                              className={
                                !r.checked ? "text-slate-400" : r.correct ? "text-emerald-600" : "text-red-600"
                              }
                            >
                              {!r.checked ? "–" : r.correct ? "✓" : "✗"}
                            </span>
                            <span className="text-slate-700 flex-1 break-all">{r.text}</span>
                            {!r.checked && r.reason && <span className="text-slate-400">({r.reason})</span>}
                            {r.checked && !r.correct && r.expected && (
                              <span className="text-slate-400">expected {r.expected}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    {gradeResult.rubric_score && (
                      <div>
                        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1">
                          Rubric score — {gradeResult.rubric_score.earned} / {gradeResult.rubric_score.possible}
                        </div>
                        <table className="w-full text-xs">
                          <tbody>
                            {gradeResult.rubric_score.breakdown.map((b, i) => (
                              <tr key={i} className="border-t border-slate-100">
                                <td className="py-1 pr-2 text-slate-500">{b.label}</td>
                                <td className="py-1 pr-2 font-mono text-slate-800">
                                  {b.points_earned}/{b.points_possible}
                                </td>
                                <td className="py-1 text-slate-400">
                                  {b.matched_line ?? (b.implied ? "implied by a later line" : "")}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                    {gradeResult.rubric_error && (
                      <p className="text-xs text-amber-700">rubric: {gradeResult.rubric_error}</p>
                    )}
                  </div>
                )}
              </section>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
