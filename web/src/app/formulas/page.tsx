"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import MathText from "@/components/MathText";
import LessonVideo from "@/components/lesson/LessonVideo";
import { api, FormulaCatalog } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";

function renderMathFormula(s: string): string {
  if (!s) return "";
  if (s.includes("$") || /[\u1780-\u17FF]/.test(s)) return s;
  return `\\(${s}\\)`;
}

function difficultyFromWeight(weight: number): "easy" | "medium" | "hard" | null {
  if (weight <= 0) return null;
  if (weight === 1) return "easy";
  if (weight === 2) return "medium";
  return "hard";
}

const DIFFICULTY_STYLES: Record<"easy" | "medium" | "hard", string> = {
  easy: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  hard: "bg-red-100 text-red-800",
};

export default function FormulasPage() {
  const { lang, t } = useLanguage();
  const [catalog, setCatalog] = useState<FormulaCatalog | null>(null);
  const [topicFilter, setTopicFilter] = useState("all");
  // One tutorial open at a time; its video loads nothing until played.
  const [watching, setWatching] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setCatalog(await api.formulas());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setBusy(false);
      }
    })();
  }, []);

  const topics = ["all", ...(catalog?.topics ?? []).map((tp) => tp.topic)];
  const visibleTopics = (catalog?.topics ?? []).filter(
    (tp) => topicFilter === "all" || tp.topic === topicFilter
  );

  const getTopicLabel = (rawTopic: string) => {
    const key = `topic_${rawTopic}` as const;
    try {
      return t(key as any) || rawTopic.replace(/_/g, " ");
    } catch {
      return rawTopic.replace(/_/g, " ");
    }
  };

  return (
    <AuthGuard>
      <div className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-1">{t("formulas_title")}</h1>
        <p className="text-sm text-slate-500 mb-6">
          {t("formulas_subtitle")}
        </p>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {busy ? (
          <p className="text-slate-500">{t("formulas_loading")}</p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2 mb-6">
              {topics.map((tp) => (
                <button
                  key={tp}
                  onClick={() => setTopicFilter(tp)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium ${
                    topicFilter === tp
                      ? "bg-slate-900 text-white"
                      : "bg-white border border-slate-300 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {tp === "all" ? t("formulas_all_topics") : getTopicLabel(tp)}
                </button>
              ))}
            </div>

            {visibleTopics.map((topicItem) => (
              <section key={topicItem.topic} className="mb-8">
                <h2 className="text-lg font-semibold text-slate-900 capitalize mb-3">
                  {getTopicLabel(topicItem.topic)}
                </h2>
                <div className="space-y-3">
                  {topicItem.entries.map((e) => {
                    const primaryName = lang === "km"
                      ? (e.name_km || e.name_en || e.id.replace(/_/g, " "))
                      : (e.name_en || e.id.replace(/_/g, " "));
                    const secondaryName = lang === "km" ? e.name_en : e.name_km;
                    const difficulty = difficultyFromWeight(e.weight);

                    return (
                      <div key={e.id} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                        <div className="flex flex-wrap items-center gap-2 text-sm">
                          <span className="font-semibold text-slate-900">
                            <MathText text={primaryName} />
                          </span>
                          {secondaryName && secondaryName !== primaryName && (
                            <span className="text-slate-500">
                              (<MathText text={secondaryName} />)
                            </span>
                          )}
                          {difficulty && (
                            <span className={`px-2 py-0.5 rounded text-xs ${DIFFICULTY_STYLES[difficulty]}`}>
                              {t(`formulas_difficulty_${difficulty}` as const)}
                            </span>
                          )}
                          <div className="ml-auto flex items-center gap-2">
                            {e.animation && (
                              <button
                                onClick={() => setWatching(watching === e.id ? null : e.id)}
                                aria-pressed={watching === e.id}
                                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium transition ${
                                  watching === e.id
                                    ? "border-sky-500 bg-sky-500 text-white"
                                    : "border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100"
                                }`}
                              >
                                <svg viewBox="0 0 16 16" className="h-3 w-3" fill="currentColor" aria-hidden>
                                  <path d="M4 2.5v11l9-5.5z" />
                                </svg>
                                {t("formulas_watch")}
                              </button>
                            )}
                            {e.variants.length > 0 && (
                              <Link
                                href={`/practice?formula=${e.id}`}
                                className="px-2.5 py-1 rounded-md bg-slate-900 text-white text-xs font-medium hover:bg-slate-700"
                              >
                                {t("formulas_practice")}
                              </Link>
                            )}
                          </div>
                        </div>
                        {e.latex && (
                          <div className="mt-2 text-slate-700">
                            <MathText text={renderMathFormula(e.latex)} />
                          </div>
                        )}
                        {e.formulas.length > 0 && (
                          <ul className="mt-2 space-y-1 text-sm text-slate-600">
                            {e.formulas.map((f, i) => (
                              <li key={i} className="leading-relaxed">
                                <MathText text={renderMathFormula(f)} />
                              </li>
                            ))}
                          </ul>
                        )}
                        {e.animation && watching === e.id && (
                          <div className="mt-4">
                            <LessonVideo animation={e.animation} />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </>
        )}
      </div>
    </AuthGuard>
  );
}
