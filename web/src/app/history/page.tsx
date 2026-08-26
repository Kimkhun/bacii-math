"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthGuard from "@/components/AuthGuard";
import MathText from "@/components/MathText";
import { api, Attempt } from "@/lib/api";

export default function HistoryPage() {
  const router = useRouter();
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.attempts();
        setAttempts(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setBusy(false);
      }
    })();
  }, []);

  const openInPractice = (a: Attempt) => router.push(`/practice?attempt=${a.id}`);

  const missedFormulas = (a: Attempt) =>
    (a.formula_breakdown ?? []).filter((f) => !f.reached);

  return (
    <AuthGuard>
      <div className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-6">History</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {busy ? (
          <p className="text-slate-500">Loading...</p>
        ) : attempts.length === 0 ? (
          <p className="text-slate-500">No attempts yet — head to Practice.</p>
        ) : (
          <div className="space-y-4">
            {attempts.map((a) => {
              const missed = missedFormulas(a);
              return (
                <div
                  key={a.id}
                  className={`bg-white border rounded-lg p-4 shadow-sm cursor-pointer hover:shadow-md transition-shadow ${
                    a.correct ? "border-emerald-200" : "border-red-200"
                  }`}
                  onClick={() => openInPractice(a)}
                >
                  <div className="flex flex-wrap items-center gap-2 mb-2 text-xs text-slate-500">
                    <span className="px-2 py-0.5 rounded bg-slate-100 capitalize">
                      {a.topic.replace("_", " ")}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-100">
                      {a.question_type.replace("_", " ")}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-100">{a.difficulty}</span>
                    <span
                      className={`px-2 py-0.5 rounded ${
                        a.correct ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
                      }`}
                    >
                      {a.correct ? "Correct" : "Wrong"}
                    </span>
                    {!!a.hints_used && (
                      <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-700">
                        {a.hints_used} hint{a.hints_used === 1 ? "" : "s"} used
                      </span>
                    )}
                    <span className="ml-auto">{new Date(a.created_at).toLocaleString()}</span>
                  </div>

                  <div className="text-sm text-slate-900">
                    {a.prompt_latex ? (
                      <MathText text={`\\(${a.prompt_latex}\\)`} />
                    ) : (
                      <p className="whitespace-pre-line">{a.prompt}</p>
                    )}
                  </div>

                  <div className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
                    <div className="text-slate-600">
                      <span className="text-slate-400">Your answer:</span>{" "}
                      <MathText text={`\\(${a.user_answer}\\)`} className="inline" />
                    </div>
                    {!a.correct && (
                      <div className="text-slate-600">
                        <span className="text-slate-400">Expected:</span>{" "}
                        <MathText text={`\\(${a.expected_answer}\\)`} className="inline" />
                      </div>
                    )}
                  </div>

                  {missed.length > 0 && (
                    <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
                      <span className="text-slate-400">Missed formulas:</span>
                      {missed.map((f, i) => (
                        <span
                          key={`${f.formula}-${i}`}
                          className="px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200"
                        >
                          {f.formula.replaceAll("_", " ")}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="mt-3 flex items-center justify-end">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openInPractice(a);
                      }}
                      className="px-3 py-1.5 rounded-md bg-slate-900 text-white text-xs font-medium hover:bg-slate-700"
                    >
                      Review
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}