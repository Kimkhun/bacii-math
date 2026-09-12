"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthGuard from "@/components/AuthGuard";
import MathText from "@/components/MathText";
import { api, Attempt } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { QUESTION_TYPE_LABELS } from "@/lib/i18n";

export default function HistoryPage() {
  const { lang, t } = useLanguage();
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

  const getTopicLabel = (topic: string) => {
    const key = `topic_${topic}` as const;
    try {
      return t(key as any) || topic.replace(/_/g, " ");
    } catch {
      return topic.replace(/_/g, " ");
    }
  };

  const getDiffLabel = (diff: string) => {
    const key = `diff_${diff}` as const;
    try {
      return t(key as any) || diff;
    } catch {
      return diff;
    }
  };

  return (
    <AuthGuard>
      <div className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-6">{t("history_title")}</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {busy ? (
          <p className="text-slate-500">{t("history_loading")}</p>
        ) : attempts.length === 0 ? (
          <p className="text-slate-500">{t("history_no_attempts")}</p>
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
                      {getTopicLabel(a.topic)}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-100">
                      {QUESTION_TYPE_LABELS[a.question_type]?.[lang] ?? a.question_type.replace(/_/g, " ")}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-100">{getDiffLabel(a.difficulty)}</span>
                    <span
                      className={`px-2 py-0.5 rounded ${
                        a.correct ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
                      }`}
                    >
                      {a.correct ? t("verdict_correct") : t("verdict_incorrect")}
                    </span>
                    {!!a.hints_used && (
                      <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-700">
                        {a.hints_used} {lang === "km" ? "ជំនួយ" : `hint${a.hints_used === 1 ? "" : "s"} used`}
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
                      <span className="text-slate-400">{t("verdict_you")}:</span>{" "}
                      <MathText text={`\\(${a.user_answer}\\)`} className="inline" />
                    </div>
                    {!a.correct && (
                      <div className="text-slate-600">
                        <span className="text-slate-400">{t("label_expected")}:</span>{" "}
                        <MathText text={`\\(${a.expected_answer}\\)`} className="inline" />
                      </div>
                    )}
                  </div>

                  {a.strokes_thumb && (
                    <img
                      src={a.strokes_thumb}
                      alt="Your handwriting"
                      className="mt-2 max-h-36 w-auto max-w-full rounded border border-slate-200 bg-white shadow-sm object-contain"
                    />
                  )}

                  {missed.length > 0 && (
                    <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
                      <span className="text-slate-400">{lang === "km" ? "រូបមន្តខ្វះចន្លោះ:" : "Missed formulas:"}</span>
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
                      {lang === "km" ? "ពិនិត្យឡើងវិញ" : "Review"}
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