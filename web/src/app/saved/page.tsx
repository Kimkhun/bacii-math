"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import MathText from "@/components/MathText";
import { api, SessionSummary } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { QUESTION_TYPE_LABELS } from "@/lib/i18n";

export default function SavedExercisesPage() {
  const { lang, t } = useLanguage();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState<"all" | "in_progress" | "completed">("all");
  const [selectedTopic, setSelectedTopic] = useState<string>("all");

  useEffect(() => {
    (async () => {
      setBusy(true);
      try {
        const data = await api.myProgress();
        setSessions(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load saved exercises");
      } finally {
        setBusy(false);
      }
    })();
  }, []);

  const deleteSession = async (id: string) => {
    if (!window.confirm(lang === "km" ? "តើអ្នកប្រាកដថាចង់លុបលំហាត់នេះទេ?" : "Are you sure you want to delete this saved exercise?")) {
      return;
    }
    try {
      await api.deleteProgress(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const topics = useMemo(() => {
    const set = new Set<string>();
    sessions.forEach((s) => {
      if (s.question?.topic) set.add(s.question.topic);
    });
    return Array.from(set);
  }, [sessions]);

  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      const isDone = s.status === "completed" || s.parts_done >= s.parts_total;
      if (filterStatus === "in_progress" && isDone) return false;
      if (filterStatus === "completed" && !isDone) return false;
      if (selectedTopic !== "all" && s.question?.topic !== selectedTopic) return false;
      return true;
    });
  }, [sessions, filterStatus, selectedTopic]);

  const getTopicLabel = (topic: string) => {
    const key = `topic_${topic}` as const;
    try {
      return t(key as any) || topic.replace(/_/g, " ");
    } catch {
      return topic.replace(/_/g, " ");
    }
  };

  return (
    <AuthGuard>
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Top Breadcrumb & Actions */}
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Link
              href="/profile"
              className="hover:text-slate-900 transition-colors inline-flex items-center gap-1"
            >
              <span>←</span>
              <span>{t("nav_profile")}</span>
            </Link>
            <span>/</span>
            <span className="text-slate-900 font-medium">{t("saved_shelf_title")}</span>
          </div>

          <Link
            href="/practice"
            className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition-colors shadow-sm"
          >
            {lang === "km" ? "ហ្វឹកហាត់លំហាត់ថ្មី" : "New Practice"}
          </Link>
        </div>

        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-baseline gap-3">
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">
              {t("saved_shelf_title")}
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
              {sessions.length}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            {lang === "km"
              ? "លំហាត់ទាំងអស់ដែលអ្នកបានរក្សាទុក ឬកំពុងដំណើរការ។ អ្នកអាចបន្តធ្វើបានគ្រប់ពេល។"
              : "All exercises you have saved or have in progress. Resume anytime right where you left off."}
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6 bg-white border border-slate-200 rounded-xl p-3 shadow-xs">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
            <button
              onClick={() => setFilterStatus("all")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                filterStatus === "all"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {lang === "km" ? "ទាំងអស់" : "All"} ({sessions.length})
            </button>
            <button
              onClick={() => setFilterStatus("in_progress")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                filterStatus === "in_progress"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {t("saved_in_progress")} (
              {sessions.filter((s) => s.status !== "completed" && s.parts_done < s.parts_total).length}
              )
            </button>
            <button
              onClick={() => setFilterStatus("completed")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                filterStatus === "completed"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {t("saved_completed")} (
              {sessions.filter((s) => s.status === "completed" || s.parts_done >= s.parts_total).length}
              )
            </button>
          </div>

          {/* Topic Selector */}
          {topics.length > 0 && (
            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-500 font-medium">
                {t("label_topic")}:
              </label>
              <select
                value={selectedTopic}
                onChange={(e) => setSelectedTopic(e.target.value)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
              >
                <option value="all">{lang === "km" ? "គ្រប់ប្រធានបទ" : "All topics"}</option>
                {topics.map((top) => (
                  <option key={top} value={top}>
                    {getTopicLabel(top)}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Content Area */}
        {error && (
          <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700 mb-6">
            {error}
          </div>
        )}

        {busy ? (
          <div className="py-16 text-center text-slate-400 text-sm">
            <div className="inline-block w-6 h-6 border-2 border-slate-300 border-t-amber-500 rounded-full animate-spin mb-2" />
            <p>{lang === "km" ? "កំពុងផ្ទុកទិន្នន័យ..." : "Loading saved exercises..."}</p>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-xs">
            <h3 className="text-base font-semibold text-slate-800 mb-1">
              {t("saved_empty")}
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
              {filterStatus !== "all" || selectedTopic !== "all"
                ? (lang === "km" ? "មិនមានលំហាត់ស្របតាមលក្ខខណ្ឌចម្រាញ់នេះទេ។" : "No exercises match this filter.")
                : (lang === "km" ? "រាល់ពេលអ្នកធ្វើលំហាត់ វឌ្ឍនភាពនឹងត្រូវបានរក្សាទុកដោយស្វ័យប្រវត្តិនៅទីនេះ។" : "Whenever you practice, your progress is automatically saved here.")}
            </p>
            <Link
              href="/practice"
              className="inline-flex items-center px-4 py-2 rounded-md bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition-colors"
            >
              {lang === "km" ? "ចាប់ផ្ដើមធ្វើលំហាត់" : "Start Practicing"}
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSessions.map((s) => {
              const typeLabel =
                QUESTION_TYPE_LABELS[s.question?.question_type ?? ""]?.[lang] ??
                s.question?.question_type.replace(/_/g, " ") ??
                "Exercise";
              const partsTotal = Math.max(1, s.parts_total || 1);
              const partsDone = s.parts_done || 0;
              const isMultiPart = s.parts_total > 1;
              const isDone = s.status === "completed" || partsDone >= partsTotal;
              const partsPercent = isMultiPart
                ? Math.round((partsDone / partsTotal) * 100)
                : (isDone ? 100 : 0);
              const dateStr = new Date(s.updated_at).toLocaleDateString(
                lang === "km" ? "km-KH" : "en-US",
                { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }
              );

              return (
                <div
                  key={s.id}
                  className="bg-white border border-slate-200 hover:border-slate-300 rounded-lg p-5 shadow-xs hover:shadow-sm transition-all flex flex-col justify-between"
                >
                  <div>
                    {/* Top Badges & Delete */}
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700">
                          {typeLabel}
                        </span>
                        {s.question?.difficulty && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold text-slate-400">
                            {s.question.difficulty}
                          </span>
                        )}
                        {isDone ? (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                            {t("saved_completed")}
                          </span>
                        ) : null}
                      </div>

                      <button
                        onClick={() => deleteSession(s.id)}
                        title={t("tip_delete_progress")}
                        className="w-6 h-6 flex items-center justify-center rounded-md text-slate-400 hover:text-red-600 hover:bg-red-50 text-xs transition-colors shrink-0"
                      >
                        ✕
                      </button>
                    </div>

                    {/* Question Prompt Preview */}
                    <div className="text-xs text-slate-700 font-medium line-clamp-3 mb-4 min-h-[48px]">
                      {s.question?.prompt_latex ? (
                        <MathText text={s.question.prompt} />
                      ) : (
                        <span>{s.question?.prompt || "Exercise in progress..."}</span>
                      )}
                    </div>

                    {/* Progress Bar */}
                    <div className="mb-4 bg-slate-50 border border-slate-100 rounded-lg p-2.5">
                      <div className="flex justify-between items-center text-[11px] text-slate-500 mb-1.5">
                        <span className="font-medium">
                          {isMultiPart
                            ? lang === "km"
                              ? `ផ្នែកទី ${partsDone}/${partsTotal}`
                              : `Part ${partsDone} of ${partsTotal}`
                            : isDone
                            ? t("saved_completed")
                            : t("saved_in_progress")}
                        </span>
                        <span className="font-semibold text-slate-600">
                          {isDone
                            ? (lang === "km" ? "រួចរាល់" : "Done")
                            : isMultiPart
                            ? `${partsPercent}%`
                            : ""}
                        </span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${
                            isDone ? "bg-emerald-500" : "bg-amber-500"
                          }`}
                          style={{
                            width: isMultiPart
                              ? `${Math.max(partsPercent, 6)}%`
                              : isDone
                              ? "100%"
                              : "40%",
                          }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Bottom Footer Action */}
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                    <span className="text-[11px] text-slate-400">
                      {dateStr}
                    </span>

                    <Link
                      href={`/practice?session=${s.id}`}
                      className="px-3.5 py-1.5 rounded-md bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition-colors"
                    >
                      {t("action_resume")}
                    </Link>
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
