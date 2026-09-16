"use client";

import { useEffect, useState } from "react";

import MathText from "@/components/MathText";
import { api, Lesson } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";

/**
 * The small window behind the profile's "Lesson" button. Fetches the authored,
 * reusable lesson for one skill and renders it in the reader's language. The
 * content is static (never LLM-generated), so this is a plain read — no
 * regeneration, no per-user state.
 */
export default function LessonModal({
  skillKey,
  fallbackLabel,
  onClose,
}: {
  skillKey: string;
  fallbackLabel: string;
  onClose: () => void;
}) {
  const { lang, t } = useLanguage();
  const km = lang === "km";
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const l = await api.lesson(skillKey);
        if (alive) setLesson(l);
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : t("lesson_none"));
      } finally {
        if (alive) setBusy(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [skillKey, t]);

  // Close on Escape, matching the click-outside affordance.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const title = lesson ? (km ? lesson.title_km : lesson.title_en) : fallbackLabel;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="my-6 w-full max-w-2xl rounded-2xl bg-white shadow-2xl border border-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Topbar */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 bg-slate-50/80 rounded-t-2xl">
          <div className="flex items-center gap-2 min-w-0">
            <span className="shrink-0 rounded-md bg-sky-100 text-sky-700 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide">
              {t("lesson")}
            </span>
            <h2 className="font-bold text-slate-900 truncate">{title}</h2>
          </div>
          <button
            className="shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-500 hover:bg-slate-200 transition"
            onClick={onClose}
          >
            {km ? "បិទ" : "Close"}
          </button>
        </div>

        {/* Content */}
        <div className="max-h-[80vh] overflow-y-auto overflow-x-hidden px-5 sm:px-6 py-5 space-y-6">
          {busy ? (
            <p className="text-slate-500 text-sm">{t("lesson_loading")}</p>
          ) : error || !lesson ? (
            <p className="text-slate-500 text-sm">{error || t("lesson_none")}</p>
          ) : (
            <>
              {/* Summary */}
              <div className="text-[15px] leading-relaxed text-slate-700">
                <MathText text={km ? lesson.summary_km : lesson.summary_en} />
              </div>

              {/* Key formulas */}
              {lesson.formulas.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    {t("lesson_key_formulas")}
                  </h3>
                  <div className="space-y-3">
                    {lesson.formulas.map((f, i) => {
                      const note = km ? f.note_km : f.note_en;
                      return (
                        <div
                          key={i}
                          className="rounded-lg border border-slate-200 bg-slate-50/70 px-4 py-3"
                        >
                          <div className="overflow-x-auto text-slate-900">
                            <MathText text={`\\[${f.latex}\\]`} />
                          </div>
                          {note && (
                            <p className="mt-1.5 text-xs text-slate-500 leading-relaxed">{note}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Explanatory sections */}
              {lesson.sections.map((s, i) => (
                <div key={i}>
                  <h3 className="font-semibold text-slate-900 text-sm mb-1.5">
                    {km ? s.heading_km : s.heading_en}
                  </h3>
                  <div className="text-[15px] leading-relaxed text-slate-700">
                    <MathText text={km ? s.body_km : s.body_en} />
                  </div>
                </div>
              ))}

              {/* Worked examples */}
              {lesson.examples.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    {t("lesson_worked_examples")}
                  </h3>
                  <div className="space-y-4">
                    {lesson.examples.map((ex, i) => (
                      <div
                        key={i}
                        className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                      >
                        <div className="font-semibold text-slate-900 text-sm mb-2">
                          <MathText text={km ? ex.prompt_km : ex.prompt_en} />
                        </div>
                        <div className="space-y-2 pl-3 border-l-2 border-slate-100">
                          {ex.steps.map((st, j) => (
                            <div key={j} className="text-[15px] leading-relaxed text-slate-700">
                              <MathText text={km ? st.text_km : st.text_en} />
                              {st.latex && (
                                <div className="mt-1 overflow-x-auto text-slate-900">
                                  <MathText text={`\\[${st.latex}\\]`} />
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                        {ex.answer_latex && (
                          <div className="mt-3 flex flex-wrap items-baseline gap-2 border-t border-slate-100 pt-2">
                            <span className="text-xs font-semibold text-emerald-700">
                              {t("lesson_answer")}
                            </span>
                            <div className="overflow-x-auto text-slate-900 font-medium">
                              <MathText text={`\\(${ex.answer_latex}\\)`} />
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
