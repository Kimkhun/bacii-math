"use client";

import { useRef, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import Canvas, { CanvasHandle } from "@/components/Canvas";
import QuestionCard from "@/components/QuestionCard";
import { api, Question, GradeResult, Explanation } from "@/lib/api";

export default function PracticePage() {
  const canvasRef = useRef<CanvasHandle>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [question, setQuestion] = useState<Question | null>(null);
  const [mode, setMode] = useState("templates");
  const [difficulty, setDifficulty] = useState("medium");
  const [typed, setTyped] = useState("");
  const [detected, setDetected] = useState<string | null>(null);
  const [result, setResult] = useState<GradeResult | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const newQuestion = async () => {
    setError("");
    setResult(null);
    setExplanation(null);
    setDetected(null);
    setTyped("");
    canvasRef.current?.clear();
    setBusy(true);
    try {
      const q = await api.generate(mode, difficulty);
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
      const img = new Image();
      img.onload = () => {
        const canvasEl = document.createElement("canvas");
        canvasEl.width = img.width;
        canvasEl.height = img.height;
        canvasEl.getContext("2d")!.drawImage(img, 0, 0);
        const b64 = canvasEl.toDataURL("image/png").split(",")[1];
        canvasRef.current?.clear();
        // draw the uploaded image onto the visible canvas
        const ctx = (document.querySelector("canvas") as HTMLCanvasElement | null)?.getContext("2d");
        if (ctx) {
          ctx.fillStyle = "#fff";
          ctx.fillRect(0, 0, 640, 360);
          const scale = Math.min(640 / img.width, 360 / img.height);
          const w = img.width * scale;
          const h = img.height * scale;
          ctx.drawImage(img, (640 - w) / 2, (360 - h) / 2, w, h);
        }
        setPendingImage(b64);
      };
      img.src = reader.result as string;
    };
    reader.readAsDataURL(file);
  };

  const [pendingImage, setPendingImage] = useState<string | null>(null);

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
      if (!answer) {
        const ink = pendingImage ?? canvasRef.current?.getImageBase64();
        if (!ink) {
          setError("Write an answer, upload an image, or type one.");
          return;
        }
        const det = await api.detect(ink);
        setDetected(det.raw_text || "(nothing detected)");
        if (!det.raw_text) {
          setError("Could not read the handwriting. Try writing larger or clearer.");
          return;
        }
        answer = det.raw_text;
      }
      const res = await api.grade(question.id, answer);
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
      const exp = await api.explain(question.id);
      setExplanation(exp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Explain failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthGuard>
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={newQuestion}
            disabled={busy}
            className="px-4 py-2 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-700 disabled:opacity-50"
          >
            New Question
          </button>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-md"
          >
            <option value="templates">Templates</option>
            <option value="gemini">Gemini</option>
          </select>
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-md"
          >
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <div className="space-y-4">
            {question ? (
              <QuestionCard
                prompt={question.prompt}
                questionType={question.question_type}
                difficulty={question.difficulty}
              />
            ) : (
              <div className="bg-white border border-slate-200 rounded-lg p-5 text-slate-500">
                Click “New Question” to start.
              </div>
            )}

            <Canvas ref={canvasRef} />
            <div className="flex items-center gap-3">
              <button
                onClick={uploadImage}
                className="px-3 py-1.5 rounded border border-slate-300 text-sm hover:bg-slate-50"
              >
                Upload image...
              </button>
              <button
                onClick={() => {
                  canvasRef.current?.clear();
                  setPendingImage(null);
                  setDetected(null);
                }}
                className="px-3 py-1.5 rounded border border-slate-300 text-sm hover:bg-slate-50"
              >
                Clear
              </button>
              <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onFile} />
            </div>

            <div className="flex items-center gap-3">
              <label className="text-sm text-slate-600">Or type:</label>
              <input
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                placeholder="e.g. 5 or pi/4"
                className="flex-1 px-3 py-2 border border-slate-300 rounded-md"
              />
            </div>

            <button
              onClick={check}
              disabled={busy}
              className="px-4 py-2 rounded-md bg-emerald-600 text-white font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              {busy ? "Working..." : "Check Answer"}
            </button>
          </div>

          <div className="space-y-4">
            {detected !== null && (
              <div className="bg-white border border-slate-200 rounded-lg p-4">
                <div className="text-xs text-slate-500 uppercase font-medium">Detected</div>
                <div className="mt-1 text-lg font-semibold">{detected}</div>
              </div>
            )}

            {result && (
              <div
                className={`rounded-lg p-4 border ${
                  result.correct ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"
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

            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-900">Explanation</h3>
              <button
                onClick={showExplanation}
                disabled={busy || !question}
                className="px-3 py-1.5 rounded-md border border-slate-300 text-sm hover:bg-slate-50 disabled:opacity-50"
              >
                Show steps
              </button>
            </div>
            {explanation ? (
              <div className="bg-white border border-slate-200 rounded-lg p-4 whitespace-pre-wrap text-sm leading-relaxed">
                {explanation.content}
                <div className="mt-3 text-xs text-slate-400">
                  {explanation.provider}
                  {explanation.intervened ? " · AI" : ""}
                </div>
              </div>
            ) : (
              <div className="bg-white border border-slate-200 rounded-lg p-4 text-sm text-slate-400">
                {result?.correct
                  ? "Nice work! No explanation needed — click “Show steps” to see it."
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
