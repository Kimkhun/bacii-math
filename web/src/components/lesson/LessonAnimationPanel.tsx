"use client";

import { useState } from "react";

import { getExplorer } from "@/components/explorers";
import LessonVideo from "@/components/lesson/LessonVideo";
import { useLanguage } from "@/context/LanguageContext";
import { LessonAnimation } from "@/lib/api";

type Mode = "watch" | "explore" | null;

function clock(seconds?: number) {
  if (!seconds) return "";
  const s = Math.round(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/**
 * The "Watch" / "Explore" buttons of an animated lesson. Nothing is fetched
 * until one is pressed: the video uses preload="none" and the explorer's code
 * is a separate lazily-loaded chunk.
 */
export default function LessonAnimationPanel({
  animation,
  onTrySimilar,
}: {
  animation: LessonAnimation;
  onTrySimilar?: () => void;
}) {
  const { t } = useLanguage();
  const [mode, setMode] = useState<Mode>(null);
  const Explorer = animation.explorer ? getExplorer(animation.explorer) : null;

  const tab = (m: Exclude<Mode, null>, label: string, icon: React.ReactNode, extra?: string) => (
    <button
      onClick={() => setMode(mode === m ? null : m)}
      aria-pressed={mode === m}
      className={`flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold transition stylus:py-3.5 ${
        mode === m
          ? "border-sky-500 bg-sky-500 text-[#ffffff] shadow-sm"
          : "border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100"
      }`}
    >
      {icon}
      {label}
      {extra && <span className={`text-xs font-normal ${mode === m ? "text-[#ffffff]/80" : "text-sky-500"}`}>{extra}</span>}
    </button>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {tab(
          "watch",
          t("lesson_watch"),
          <svg viewBox="0 0 16 16" className="h-4 w-4" fill="currentColor" aria-hidden>
            <path d="M4 2.5v11l9-5.5z" />
          </svg>,
          clock(animation.duration),
        )}
        {Explorer &&
          tab(
            "explore",
            t("lesson_explore"),
            <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
              <path d="M2 4h12M2 8h12M2 12h12" strokeLinecap="round" />
              <circle cx="5" cy="4" r="1.6" fill="currentColor" />
              <circle cx="10" cy="8" r="1.6" fill="currentColor" />
              <circle cx="7" cy="12" r="1.6" fill="currentColor" />
            </svg>,
          )}
      </div>
      {mode === "watch" && <LessonVideo animation={animation} onTrySimilar={onTrySimilar} />}
      {mode === "explore" && Explorer && <Explorer />}
    </div>
  );
}
