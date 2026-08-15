"use client";

import { useEffect, useRef, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import Canvas, { CanvasHandle, CanvasTool, PEN_WIDTHS } from "@/components/Canvas";
import MathText from "@/components/MathText";
import QuestionCard from "@/components/QuestionCard";
import { api, Question, GradeResult, Explanation, DetectResult } from "@/lib/api";

export default function PracticePage() {
  const canvasRef = useRef<CanvasHandle>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [question, setQuestion] = useState<Question | null>(null);
  const [mode, setMode] = useState("templates");
  const [topic, setTopic] = useState("complex");
  const [difficulty, setDifficulty] = useState("medium");
  const [typed, setTyped] = useState("");
  const [detected, setDetected] = useState<string | null>(null);
  const [workText, setWorkText] = useState<string | null>(null);
  const [result, setResult] = useState<GradeResult | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [debug, setDebug] = useState(false);
  const [detectResult, setDetectResult] = useState<DetectResult | null>(null);
  const [tool, setTool] = useState<CanvasTool>("pen");
  const [penWidth, setPenWidth] = useState<number>(PEN_WIDTHS.medium);
  const [canUndo, setCanUndo] = useState(false);
  const [zoom, setZoom] = useState(1);

  const selectTool = (t: CanvasTool) => {
    setTool(t);
    canvasRef.current?.setTool(t);
  };

  const selectPenWidth = (w: number) => {
    setPenWidth(w);
    canvasRef.current?.setPenWidth(w);
  };

  const undo = () => canvasRef.current?.undo();

  const markDirty = () => setCanUndo(canvasRef.current?.canUndo() ?? false);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        undo();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const zoomIn = () => setZoom((z) => Math.min(2.5, Math.round((z + 0.25) * 100) / 100));
  const zoomOut = () => setZoom((z) => Math.max(0.5, Math.round((z - 0.25) * 100) / 100));
  const zoomReset = () => setZoom(1);

  const newQuestion = async () => {
    setError("");
    setResult(null);
    setExplanation(null);
    setDetected(null);
    setWorkText(null);
    setDetectResult(null);
    setTyped("");
    canvasRef.current?.clear();
    setBusy(true);
    try {
      const q = await api.generate(topic === "calculus" ? "templates" : mode, difficulty, topic);
      setQuestion(q);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate");
    } finally {
      setBusy(false);
    }
  };

  const uploadImage = () => fileRef.current?.click();

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      canvasRef.current?.loadImage(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const check = async () => {
    if (!question) {
      setError("Generate a question first.");
      return;
    }
    setError("");
    setResult(null);
    setExplanation(null);
    setBusy(true);
    try {
      let answer = typed.trim();
      let work: string | undefined;
      if (!answer) {
        const ink = canvasRef.current?.getImageBase64();
        if (!ink) {
          setError("Write an answer on the page, upload an image, or type one.");
          return;
        }
        const det = await api.detect(ink);
        setDetectResult(det);
        setDetected(det.raw_text || "(nothing detected)");
        work = det.lines?.length ? det.lines.join("\n") : undefined;
        setWorkText(work ?? null);
        if (!det.raw_text) {
          setError("Could not read the handwriting. Try writing larger or clearer.");
          return;
        }
        answer = det.raw_text;
      }
      const res = await api.grade(question.id, answer, work);
      setResult(res);
      if (res.explanation) setExplanation(res.explanation);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Check failed");
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

  return (
    <AuthGuard>
      <div className="relative">
        <Canvas ref={canvasRef} fullscreen zoom={zoom} onChange={markDirty} onZoomChange={setZoom} />

        <div className="fixed inset-x-3 top-3 z-10 flex flex-wrap items-start justify-between gap-3 pointer-events-none">
          <div className="pointer-events-auto w-full sm:w-auto sm:max-w-md sm:flex-1">
            {question ? (
              <QuestionCard
                prompt={question.prompt}
                promptLatex={question.prompt_latex}
                questionType={question.question_type}
                difficulty={question.difficulty}
              />
            ) : (
              <div className="bg-white/90 backdrop-blur border border-slate-200 rounded-lg p-4 text-slate-500 shadow-md">
                Click “New Question” to start.
              </div>
            )}
          </div>

          <div className="pointer-events-auto w-full sm:w-auto sm:max-w-md bg-white/90 backdrop-blur border border-slate-200 rounded-lg shadow-md p-3 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={newQuestion}
                disabled={busy}
                className="px-3 py-2 rounded-md bg-slate-900 text-white text-sm font-medium hover:bg-slate-700 disabled:opacity-50"
              >
                New Question
              </button>
              <select
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                className="px-2 py-2 border border-slate-300 rounded-md text-sm"
              >
                <option value="complex">Complex numbers</option>
                <option value="calculus">Calculus</option>
              </select>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                disabled={topic === "calculus"}
                className="px-2 py-2 border border-slate-300 rounded-md text-sm disabled:opacity-50"
              >
                <option value="templates">Templates</option>
                <option value="gemini">Gemini</option>
              </select>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="px-2 py-2 border border-slate-300 rounded-md text-sm"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
              <button
                onClick={uploadImage}
                className="px-3 py-2 rounded border border-slate-300 text-sm hover:bg-slate-50"
              >
                Upload image...
              </button>
              <div className="flex rounded-md border border-slate-300 overflow-hidden text-sm">
                <button
                  onClick={() => selectTool("pen")}
                  className={`px-3 py-2 ${tool === "pen" ? "bg-slate-900 text-white" : "hover:bg-slate-50"}`}
                >
                  Pen
                </button>
                <button
                  onClick={() => selectTool("eraser")}
                  className={`px-3 py-2 border-l border-slate-300 ${
                    tool === "eraser" ? "bg-slate-900 text-white" : "hover:bg-slate-50"
                  }`}
                >
                  Eraser
                </button>
              </div>
              <div className="flex rounded-md border border-slate-300 overflow-hidden text-sm">
                {(["thin", "medium", "thick"] as const).map((size, i) => (
                  <button
                    key={size}
                    onClick={() => selectPenWidth(PEN_WIDTHS[size])}
                    title={size}
                    className={`px-3 py-2 ${i > 0 ? "border-l border-slate-300" : ""} ${
                      penWidth === PEN_WIDTHS[size] ? "bg-slate-900 text-white" : "hover:bg-slate-50"
                    }`}
                  >
                    <span
                      className={`inline-block rounded-full ${penWidth === PEN_WIDTHS[size] ? "bg-white" : "bg-slate-700"}`}
                      style={{ width: PEN_WIDTHS[size], height: PEN_WIDTHS[size] }}
                    />
                  </button>
                ))}
              </div>
              <button
                onClick={undo}
                disabled={!canUndo}
                className="px-3 py-2 rounded border border-slate-300 text-sm hover:bg-slate-50 disabled:opacity-50"
              >
                Undo
              </button>
              <div className="flex items-center rounded-md border border-slate-300 overflow-hidden text-sm">
                <button onClick={zoomOut} className="px-2.5 py-2 hover:bg-slate-50" title="Zoom out">
                  −
                </button>
                <button
                  onClick={zoomReset}
                  className="px-2 py-2 border-x border-slate-300 hover:bg-slate-50 min-w-[3.5rem] text-center"
                  title="Reset zoom"
                >
                  {Math.round(zoom * 100)}%
                </button>
                <button onClick={zoomIn} className="px-2.5 py-2 hover:bg-slate-50" title="Zoom in">
                  +
                </button>
              </div>
              <button
                onClick={() => {
                  canvasRef.current?.clear();
                  setDetected(null);
                  setWorkText(null);
                  setDetectResult(null);
                }}
                className="px-3 py-2 rounded border border-slate-300 text-sm hover:bg-slate-50"
              >
                Clear
              </button>
              <label className="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={debug}
                  onChange={(e) => setDebug(e.target.checked)}
                  className="accent-slate-900"
                />
                Debug
              </label>
              <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onFile} />
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm text-slate-600 whitespace-nowrap">Or type:</label>
              <input
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                placeholder="e.g. 5 or pi/4"
                className="flex-1 px-2 py-2 border border-slate-300 rounded-md text-sm"
              />
              <button
                onClick={check}
                disabled={busy}
                className="px-4 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
              >
                {busy ? "Working..." : "Check Answer"}
              </button>
            </div>

            {error && <p className="text-xs text-red-600">{error}</p>}
          </div>
        </div>

        {debug && (
          <div className="fixed left-3 bottom-3 z-10 w-[calc(100vw-1.5rem)] sm:w-[26rem] max-h-[45vh] overflow-y-auto pointer-events-auto bg-slate-900/95 backdrop-blur text-slate-100 rounded-lg p-3 text-xs space-y-2 shadow-lg">
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
                <pre className="mt-1 whitespace-pre-wrap break-all">
                  {JSON.stringify(detectResult, null, 2)}
                </pre>
              ) : (
                "no detection yet"
              )}
            </div>
            <div>
              <span className="text-slate-400">Typed answer:</span> {typed || "(none)"}
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

        <div className="fixed right-3 bottom-3 z-10 w-[calc(100vw-1.5rem)] sm:w-96 max-h-[55vh] overflow-y-auto pointer-events-auto space-y-3">
          {detected !== null && (
            <div className="bg-white/90 backdrop-blur border border-slate-200 rounded-lg p-3 shadow-md">
              {workText && workText.split("\n").length > 1 && (
                <div className="mb-2 pb-2 border-b border-slate-200">
                  <div className="text-xs text-slate-500 uppercase font-medium">Your work</div>
                  <div className="mt-1 text-sm space-y-0.5">
                    {workText.split("\n").map((line, idx) => {
                      const errLine = result?.step_check?.first_error_line;
                      const isError = errLine === idx + 1;
                      return (
                        <div
                          key={idx}
                          className={isError ? "text-red-700 font-semibold" : "text-slate-600"}
                        >
                          {isError ? "→ " : ""}
                          {line}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              <div className="text-xs text-slate-500 uppercase font-medium">Detected answer</div>
              <div className="mt-1 text-lg font-semibold">{detected}</div>
            </div>
          )}

          {result && (
            <div
              className={`rounded-lg p-3 border shadow-md ${
                result.correct
                  ? "bg-emerald-50/95 border-emerald-200"
                  : "bg-red-50/95 border-red-200"
              }`}
            >
              <div className="font-bold text-slate-900">
                {result.correct ? "Correct" : "Incorrect"}
              </div>
              {!result.correct && (
                <div className="mt-1 text-sm text-slate-700">
                  Expected: <span className="font-medium">{result.expected}</span>
                </div>
              )}
              <div className="mt-1 text-xs text-slate-500">Reason: {result.reason}</div>
            </div>
          )}

          <div className="bg-white/90 backdrop-blur border border-slate-200 rounded-lg shadow-md p-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-900 text-sm">Explanation</h3>
              <button
                onClick={showExplanation}
                disabled={busy || !question}
                className="px-2 py-1 rounded-md border border-slate-300 text-xs hover:bg-slate-50 disabled:opacity-50"
              >
                Show steps
              </button>
            </div>
            {explanation ? (
              <div className="mt-2 text-sm leading-relaxed">
                <MathText text={explanation.content} className="whitespace-pre-wrap" />
                {explanation.work_check?.content && (
                  <div className="mt-3 border-t border-slate-200 pt-2">
                    <div className="text-xs font-medium text-slate-500 uppercase">Your work check</div>
                    <MathText text={explanation.work_check.content} className="mt-1 whitespace-pre-wrap" />
                  </div>
                )}
                <div className="mt-2 text-xs text-slate-400">
                  {explanation.provider}
                  {explanation.intervened ? " · AI" : ""}
                </div>
              </div>
            ) : (
              <div className="mt-2 text-sm text-slate-400">
                {result?.correct
                  ? "Nice work! Click “Show steps” to see it."
                  : result && !result.correct
                  ? "Click “Show steps” for a full solution."
                  : "Explanation will appear here."}
              </div>
            )}
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
