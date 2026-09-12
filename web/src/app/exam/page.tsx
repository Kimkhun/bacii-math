"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import MathText from "@/components/MathText";
import { api, Exam, ExamResult } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";

const EXAM_ID = "2018";

function formatClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function ExamPageInner() {
  const { lang, t } = useLanguage();
  const [exam, setExam] = useState<Exam | null>(null);
  const [error, setError] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [started, setStarted] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ExamResult | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    api
      .exam(EXAM_ID)
      .then((e) => {
        setExam(e);
        setSecondsLeft((e.duration_minutes ?? 150) * 60);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load exam"));
  }, []);

  const submitExam = async () => {
    if (submitting || result) return;
    setSubmitting(true);
    setError("");
    if (timerRef.current) clearInterval(timerRef.current);
    try {
      const res = await api.submitExam(EXAM_ID, answers);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit exam");
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    if (!started || secondsLeft === null || result) return;
    timerRef.current = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev === null) return prev;
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          submitExam();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [started]);

  const totalGraded = useMemo(() => {
    if (!result) return null;
    return { earned: result.earned, possible: result.possible };
  }, [result]);

  if (error && !exam) {
    return <div className="max-w-3xl mx-auto p-6 text-red-600">{error}</div>;
  }

  if (!exam) {
    return <div className="max-w-3xl mx-auto p-6 text-slate-500">Loading exam…</div>;
  }

  if (!started) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">{t("exam_title")} — {exam.exam_date}</h1>
        <p className="text-slate-600 mb-1">{t("exam_duration")}: {exam.duration_minutes} {lang === "km" ? "នាទី" : "minutes"}</p>
        <p className="text-slate-600 mb-6">{t("exam_total_points")}: {exam.total_points} {t("exam_pts")} ({exam.sections.length} {lang === "km" ? "ផ្នែក" : "sections"})</p>
        <p className="text-slate-600 mb-6 leading-relaxed">
          {t("exam_intro")}
        </p>
        <button
          onClick={() => setStarted(true)}
          className="px-5 py-2.5 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-700"
        >
          {t("btn_start_exam")}
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-6 pb-24">
      <div className="sticky top-0 z-10 bg-[#faf9f6]/95 backdrop-blur border-b border-[#e5e1d8] -mx-6 px-6 py-3 mb-6 flex items-center justify-between">
        <h1 className="text-lg font-bold text-slate-900">{t("exam_title")} — {exam.exam_date}</h1>
        {secondsLeft !== null && !result && (
          <div
            className={`font-mono text-lg font-semibold ${secondsLeft < 600 ? "text-red-600" : "text-slate-700"}`}
          >
            {formatClock(secondsLeft)}
          </div>
        )}
        {result && totalGraded && (
          <div className="font-semibold text-slate-900">
            {t("exam_score")}: {totalGraded.earned.toFixed(1)} / {totalGraded.possible.toFixed(0)} {t("exam_pts")}
          </div>
        )}
      </div>

      {error && <div className="mb-4 text-red-600 text-sm">{error}</div>}

      <div className="space-y-8">
        {exam.sections.map((section, idx) => {
          const qResult = result?.per_question[String(idx + 1)];
          const sectionTitle = (lang === "km" && section.title_km) ? section.title_km : (section.title_en ?? `Part ${section.id}`);
          const sectionGiven = (lang === "km" && section.given_km) ? section.given_km : section.given_en;

          return (
            <div key={section.id} className="bg-white border border-[#e5e1d8] rounded-lg p-5">
              <div className="flex items-center justify-between mb-2">
                <h2 className="font-semibold text-slate-900">
                  {t("exam_question")} {section.id} — {sectionTitle}
                </h2>
                {qResult && (
                  <span className="text-sm font-medium text-slate-600">
                    {qResult.earned.toFixed(1)} / {qResult.possible.toFixed(0)} {t("exam_pts")}
                  </span>
                )}
              </div>

              {(sectionGiven || section.given_latex) && (
                <div className="text-sm text-slate-700 mb-3">
                  {sectionGiven && <MathText text={sectionGiven} />}
                  {section.given_latex && <MathText text={`$${section.given_latex}$`} className="block mt-1" />}
                </div>
              )}

              <ul className="space-y-2 mb-4">
                {section.questions.map((q) => (
                  <li key={q.label} className="text-sm text-slate-800">
                    <span className="font-medium">{q.label})</span>{" "}
                    {q.prompt_en && <MathText text={q.prompt_en} />}
                    {q.prompt_latex && <MathText text={`$${q.prompt_latex}$`} />}
                    {!q.gradable && (
                      <span className="ml-2 text-xs text-slate-400 italic">
                        {lang === "km" ? "(សម្រាប់ផ្ទៀងផ្ទាត់ខ្លួនឯង)" : "(self-check only)"}
                      </span>
                    )}
                  </li>
                ))}
              </ul>

              <textarea
                value={answers[String(idx + 1)] ?? ""}
                onChange={(e) =>
                  setAnswers((prev) => ({ ...prev, [String(idx + 1)]: e.target.value }))
                }
                disabled={!!result}
                placeholder={lang === "km" ? "សូមសរសេរជំហានដោះស្រាយនៅទីនេះ មួយបន្ទាត់ម្តងៗ..." : "Write your work here, one fact/step per line…"}
                rows={5}
                className="w-full border border-[#dddad1] rounded-md p-2.5 text-sm font-mono disabled:bg-slate-50 disabled:text-slate-500"
              />

              {qResult && qResult.breakdown.length > 0 && (
                <div className="mt-3 text-xs text-slate-500 space-y-0.5">
                  {qResult.breakdown.map((b, i) => (
                    <div key={i} className={b.points_earned > 0 ? "text-green-700" : "text-slate-400"}>
                      {b.points_earned > 0 ? "✓" : "✗"} {b.item}: {b.label} ({b.points_earned.toFixed(1)}/
                      {b.points_possible.toFixed(1)})
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {!result && (
        <div className="mt-8 flex justify-end">
          <button
            onClick={submitExam}
            disabled={submitting}
            className="px-6 py-3 rounded-md bg-slate-900 text-white font-semibold hover:bg-slate-700 disabled:opacity-50"
          >
            {submitting ? t("btn_checking") : t("btn_submit_exam")}
          </button>
        </div>
      )}
    </div>
  );
}

export default function ExamPage() {
  return (
    <AuthGuard>
      <ExamPageInner />
    </AuthGuard>
  );
}
