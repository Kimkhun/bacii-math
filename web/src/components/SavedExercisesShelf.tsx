"use client";

import { useRef, useState, useEffect } from "react";
import Link from "next/link";
import { SessionSummary } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { QUESTION_TYPE_LABELS } from "@/lib/i18n";
import MathText from "@/components/MathText";

function timeAgo(dateString: string, lang: "en" | "km"): string {
  try {
    const d = new Date(dateString);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diffSec < 60) return lang === "km" ? "មុននេះបន្តិច" : "Just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) {
      return lang === "km" ? `${diffMin} នាទីមុន` : `${diffMin}m ago`;
    }
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) {
      return lang === "km" ? `${diffHour} ម៉ោងមុន` : `${diffHour}h ago`;
    }
    const diffDay = Math.floor(diffHour / 24);
    return lang === "km" ? `${diffDay} ថ្ងៃមុន` : `${diffDay}d ago`;
  } catch {
    return "";
  }
}

export default function SavedExercisesShelf({
  sessions,
  onDelete,
}: {
  sessions: SessionSummary[];
  onDelete?: (id: string) => void;
}) {
  const { lang, t } = useLanguage();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 8);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 8);
  };

  useEffect(() => {
    checkScroll();
    const el = scrollRef.current;
    if (!el) return;
    el.addEventListener("scroll", checkScroll, { passive: true });
    window.addEventListener("resize", checkScroll);
    return () => {
      el.removeEventListener("scroll", checkScroll);
      window.removeEventListener("resize", checkScroll);
    };
  }, [sessions]);

  const scroll = (direction: "left" | "right") => {
    const el = scrollRef.current;
    if (!el) return;
    const distance = direction === "left" ? -280 : 280;
    el.scrollBy({ left: distance, behavior: "smooth" });
  };

  if (!sessions || sessions.length === 0) {
    return (
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-slate-900">{t("saved_shelf_title")}</h2>
        </div>
        <div className="rounded-lg border border-dashed border-slate-200 bg-white p-6 text-center">
          <p className="text-xs text-slate-500 mb-3">
            {t("saved_empty")}
          </p>
          <Link
            href="/practice"
            className="inline-flex items-center px-3 py-1.5 rounded-md bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition-colors"
          >
            {lang === "km" ? "ចាប់ផ្ដើមធ្វើលំហាត់" : "Start Practicing"}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header outside the container to match profile styling */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold text-slate-900">{t("saved_shelf_title")}</h2>
          <span className="text-xs text-slate-400">({sessions.length})</span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Left / Right scroll navigation */}
          <button
            onClick={() => scroll("left")}
            disabled={!canScrollLeft}
            aria-label="Scroll left"
            className="w-7 h-7 flex items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-sm font-semibold"
          >
            ‹
          </button>
          <button
            onClick={() => scroll("right")}
            disabled={!canScrollRight}
            aria-label="Scroll right"
            className="w-7 h-7 flex items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-sm font-semibold"
          >
            ›
          </button>

          {/* Link to see all saved exercises */}
          <Link
            href="/saved"
            className="text-xs text-slate-500 hover:text-slate-900 transition-colors ml-1 font-medium"
          >
            {t("saved_see_all")} →
          </Link>
        </div>
      </div>

      {/* Horizontal scrolling shelf */}
      <div
        ref={scrollRef}
        className="flex gap-3 overflow-x-auto pb-2 pt-0.5 px-0.5 scroll-smooth no-scrollbar snap-x snap-mandatory"
      >
        {sessions.map((s) => {
          const typeLabel =
            QUESTION_TYPE_LABELS[s.question?.question_type ?? ""]?.[lang] ??
            s.question?.question_type.replace(/_/g, " ") ??
            "Exercise";
          const promptPreview = (s.question?.prompt ?? "").split("\n")[0] || "";
          
          const partsTotal = Math.max(1, s.parts_total || 1);
          const partsDone = s.parts_done || 0;
          const isMultiPart = s.parts_total > 1;
          const isDone = s.status === "completed" || partsDone >= partsTotal;
          const partsPercent = isMultiPart
            ? Math.round((partsDone / partsTotal) * 100)
            : (isDone ? 100 : 0);

          return (
            <div
              key={s.id}
              className="w-[270px] shrink-0 snap-start bg-white border border-slate-200 hover:border-slate-300 rounded-lg p-4 shadow-xs hover:shadow-sm transition-all flex flex-col justify-between"
            >
              <div>
                {/* Topic badge & delete action */}
                <div className="flex items-center justify-between gap-1 mb-2.5">
                  <div className="flex items-center gap-1.5 overflow-hidden">
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 truncate max-w-[150px]">
                      {typeLabel}
                    </span>
                    {s.question?.difficulty && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                        {s.question.difficulty}
                      </span>
                    )}
                  </div>

                  {onDelete && (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onDelete(s.id);
                      }}
                      title={t("tip_delete_progress")}
                      className="w-5 h-5 flex items-center justify-center rounded text-slate-400 hover:text-red-600 hover:bg-red-50 text-xs transition-colors shrink-0"
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* Prompt preview */}
                <div className="text-xs text-slate-700 font-medium line-clamp-2 h-9 mb-3">
                  {s.question?.prompt_latex ? (
                    <MathText text={promptPreview} />
                  ) : (
                    <span>{promptPreview || "Exercise in progress..."}</span>
                  )}
                </div>

                {/* Progress bar */}
                <div className="mb-3">
                  <div className="flex justify-between items-baseline text-[11px] text-slate-500 mb-1">
                    <span>
                      {isMultiPart
                        ? lang === "km"
                          ? `${partsDone}/${partsTotal} ផ្នែកបានរួចរាល់`
                          : `${partsDone}/${partsTotal} parts done`
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
                  <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
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

              {/* Bottom footer: time ago and resume button */}
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                <span className="text-[11px] text-slate-400 truncate">
                  {timeAgo(s.updated_at, lang)}
                </span>

                <Link
                  href={`/practice?session=${s.id}`}
                  className="px-3 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition-colors"
                >
                  {t("action_resume")}
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
