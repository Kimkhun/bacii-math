"use client";

import { useEffect, useRef, useState } from "react";

import MathText from "@/components/MathText";
import { useLanguage } from "@/context/LanguageContext";
import { LessonAnimation } from "@/lib/api";

const BASE = process.env.NEXT_PUBLIC_ANIMATION_BASE_URL ?? "/animations";
const QUALITY_KEY = "bacii_video_quality";

type Quality = "hd" | "sd";

// The 480p variant is picked automatically for students on metered or slow
// connections; an explicit choice is remembered per browser.
function initialQuality(): Quality {
  try {
    const saved = localStorage.getItem(QUALITY_KEY);
    if (saved === "hd" || saved === "sd") return saved;
  } catch {
    // Storage blocked: fall through to the connection hint.
  }
  const conn = (navigator as Navigator & {
    connection?: { saveData?: boolean; effectiveType?: string };
  }).connection;
  if (conn?.saveData || ["slow-2g", "2g", "3g"].includes(conn?.effectiveType ?? "")) return "sd";
  return "hd";
}

/**
 * The lesson's Manim video with captions rendered underneath in the reader's
 * language. The video carries no words, so switching language swaps only the
 * caption text — nothing is re-downloaded. `preload="none"` means no video
 * bytes move until the student presses play.
 */
export default function LessonVideo({ animation }: { animation: LessonAnimation }) {
  const { lang, t } = useLanguage();
  const km = lang === "km";
  const ref = useRef<HTMLVideoElement>(null);
  const [quality, setQuality] = useState<Quality>("hd");
  const [cueIdx, setCueIdx] = useState(0);
  const [failed, setFailed] = useState(false);
  const resume = useRef<{ time: number; playing: boolean } | null>(null);

  useEffect(() => setQuality(initialQuality()), []);

  const v = animation.version ? `?v=${animation.version}` : "";
  const src = `${BASE}/${animation.video}${quality === "sd" ? ".480" : ""}.mp4${v}`;
  const poster = `${BASE}/${animation.video}.webp${v}`;
  const cues = animation.cues;
  const cue = cues[cueIdx];

  const onTime = () => {
    const now = ref.current?.currentTime ?? 0;
    const i = cues.findIndex((c) => now >= c.start && now < c.end);
    if (i >= 0 && i !== cueIdx) setCueIdx(i);
  };

  const seek = (i: number) => {
    const el = ref.current;
    if (!el) return;
    el.currentTime = cues[i].start + 0.01;
    setCueIdx(i);
    void el.play().catch(() => {});
  };

  const switchQuality = (q: Quality) => {
    const el = ref.current;
    if (el && el.currentTime > 0) resume.current = { time: el.currentTime, playing: !el.paused };
    setQuality(q);
    try {
      localStorage.setItem(QUALITY_KEY, q);
    } catch {
      // Not remembered; fine for this session.
    }
  };

  // A quality switch remounts the <video> on the new source (still
  // preload="none"), so kick off loading only when there is a position to
  // restore; `onLoaded` then seeks back and resumes.
  useEffect(() => {
    const el = ref.current;
    const r = resume.current;
    if (!el || !r) return;
    if (r.playing) void el.play().catch(() => {});
    else {
      el.preload = "metadata";
      el.load();
    }
  }, [src]);

  // After a quality switch the element loads the new source; continue where
  // the student was.
  const onLoaded = () => {
    const el = ref.current;
    const r = resume.current;
    if (!el || !r) return;
    el.currentTime = r.time;
    if (r.playing) void el.play().catch(() => {});
    resume.current = null;
  };

  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-xl bg-[#0e1116] aspect-video">
        <video
          ref={ref}
          key={src}
          className="h-full w-full"
          controls
          playsInline
          preload="none"
          poster={poster}
          onTimeUpdate={onTime}
          onSeeked={onTime}
          onLoadedMetadata={onLoaded}
          onError={() => setFailed(true)}
          aria-describedby="lesson-caption"
        >
          <source src={src} type="video/mp4" />
        </video>
      </div>

      {failed ? (
        <p className="text-sm text-red-600">{t("lesson_video_error")}</p>
      ) : (
        <div
          id="lesson-caption"
          aria-live="polite"
          className="min-h-[4.5rem] rounded-lg bg-slate-900 px-4 py-3 text-[15px] leading-relaxed text-slate-50"
        >
          {cue && <MathText text={km ? cue.text_km : cue.text_en} />}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="mr-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t("lesson_steps")}
          </span>
          {cues.map((c, i) => (
            <button
              key={c.id}
              onClick={() => seek(i)}
              title={(km ? c.text_km : c.text_en).replace(/\$/g, "")}
              className={`h-7 min-w-7 rounded-md px-2 text-xs font-semibold transition stylus:h-9 stylus:min-w-9 ${
                i === cueIdx ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {i + 1}
            </button>
          ))}
        </div>
        <div className="flex rounded-lg bg-slate-100 p-0.5 text-xs font-medium">
          {(["hd", "sd"] as const).map((q) => (
            <button
              key={q}
              onClick={() => switchQuality(q)}
              className={`rounded-md px-2.5 py-1 transition ${
                quality === q ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {q === "hd" ? t("lesson_video_hd") : t("lesson_video_data_saver")}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
