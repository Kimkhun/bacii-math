"use client";

import { useEffect, useRef, useState } from "react";
import MathText from "@/components/MathText";
import { useLanguage } from "@/context/LanguageContext";
import { LessonAnimation } from "@/lib/api";

const BASE = process.env.NEXT_PUBLIC_ANIMATION_BASE_URL ?? "/animations";
const QUALITY_KEY = "bacii_video_quality";
const AUTOPAUSE_KEY = "bacii_video_autopause";
const SPEEDS = [0.75, 1, 1.25] as const;

type Quality = "hd" | "sd";

function initialQuality(): Quality {
  try {
    const saved = localStorage.getItem(QUALITY_KEY);
    if (saved === "hd" || saved === "sd") return saved;
  } catch {}
  const conn = (navigator as Navigator & {
    connection?: { saveData?: boolean; effectiveType?: string };
  }).connection;
  if (conn?.saveData || ["slow-2g", "2g", "3g"].includes(conn?.effectiveType ?? "")) return "sd";
  return "hd";
}

function initialAutoPause(): boolean {
  try {
    const saved = localStorage.getItem(AUTOPAUSE_KEY);
    if (saved !== null) return saved === "true";
  } catch {}
  return true;
}

function formatClock(seconds: number): string {
  if (!seconds || isNaN(seconds) || seconds < 0) return "0:00";
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}:${String(rem).padStart(2, "0")}`;
}

export default function LessonVideo({
  animation,
  onTrySimilar,
}: {
  animation: LessonAnimation;
  onTrySimilar?: () => void;
}) {
  const { lang, t } = useLanguage();
  const km = lang === "km";

  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastPausedCueRef = useRef<number | null>(null);
  const resumeRef = useRef<{ time: number; playing: boolean } | null>(null);

  const [quality, setQuality] = useState<Quality>("hd");
  const [speed, setSpeed] = useState<number>(1);
  const [autoPause, setAutoPause] = useState<boolean>(true);
  const [cueIdx, setCueIdx] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isStepPaused, setIsStepPaused] = useState(false);
  const [isEnded, setIsEnded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showOverlay, setShowOverlay] = useState(true);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const cues = animation.cues || [];
  const cue = cues[cueIdx];
  const isLastCue = cueIdx === cues.length - 1;
  const duration = animation.duration || cues[cues.length - 1]?.end || 0;

  const v = animation.version ? `?v=${animation.version}` : "";
  const src = `${BASE}/${animation.video}${quality === "sd" ? ".480" : ""}.mp4${v}`;
  const poster = `${BASE}/${animation.video}.webp${v}`;

  // Initialize saved settings
  useEffect(() => {
    setQuality(initialQuality());
    setAutoPause(initialAutoPause());

    const handleFsChange = () => {
      const isFs = !!(document.fullscreenElement || (document as any).webkitFullscreenElement);
      setIsFullscreen(isFs);
      setShowOverlay(true);
    };

    document.addEventListener("fullscreenchange", handleFsChange);
    document.addEventListener("webkitfullscreenchange", handleFsChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFsChange);
      document.removeEventListener("webkitfullscreenchange", handleFsChange);
    };
  }, []);

  // Close options menu on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    if (showMenu) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [showMenu]);

  const togglePiP = async () => {
    const el = videoRef.current;
    if (!el) return;
    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
      } else if (document.pictureInPictureEnabled) {
        await el.requestPictureInPicture();
      }
    } catch (err) {
      console.error("PiP error", err);
    } finally {
      setShowMenu(false);
    }
  };

  const downloadVideo = () => {
    const a = document.createElement("a");
    a.href = src;
    a.download = `${animation.video || "lesson"}-${quality}.mp4`;
    a.target = "_blank";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setShowMenu(false);
  };

  // Controls auto-hide manager
  const wakeOverlay = () => {
    setShowOverlay(true);
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    if (videoRef.current && !videoRef.current.paused && !showMenu) {
      hideTimerRef.current = setTimeout(() => {
        setShowOverlay(false);
      }, 3000);
    }
  };

  const toggleFullscreen = async () => {
    const container = containerRef.current;
    if (!container) return;
    try {
      const fsEl = document.fullscreenElement || (document as any).webkitFullscreenElement;
      if (!fsEl) {
        if (container.requestFullscreen) {
          await container.requestFullscreen();
        } else if ((container as any).webkitRequestFullscreen) {
          await (container as any).webkitRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          await document.exitFullscreen();
        } else if ((document as any).webkitExitFullscreen) {
          await (document as any).webkitExitFullscreen();
        }
      }
    } catch (err) {
      console.error("Fullscreen error", err);
    }
  };

  const onTimeUpdate = () => {
    const el = videoRef.current;
    if (!el) return;
    const now = el.currentTime;
    setCurrentTime(now);

    const i = cues.findIndex((c) => now >= c.start && now < c.end);
    if (i >= 0 && i !== cueIdx) {
      setCueIdx(i);
      setIsEnded(false);
    }

    // Step Auto-Pause mechanism
    if (autoPause && !el.paused && cue) {
      if (now >= cue.end - 0.08 && lastPausedCueRef.current !== cueIdx) {
        el.pause();
        lastPausedCueRef.current = cueIdx;
        setIsStepPaused(true);
        setShowOverlay(true);
        if (isLastCue) {
          setIsEnded(true);
        }
      }
    }
  };

  const seekTime = (targetTime: number) => {
    const el = videoRef.current;
    if (!el) return;
    el.currentTime = Math.max(0, Math.min(targetTime, duration));
    el.playbackRate = speed;
    lastPausedCueRef.current = null;
    setIsStepPaused(false);
    setIsEnded(false);
    wakeOverlay();
  };

  const seekCue = (i: number) => {
    if (!cues[i]) return;
    seekTime(cues[i].start + 0.01);
    setCueIdx(i);
    const el = videoRef.current;
    if (el) void el.play().catch(() => {});
  };

  const nextStep = () => {
    if (cueIdx < cues.length - 1) {
      seekCue(cueIdx + 1);
    } else {
      setIsEnded(true);
      setShowOverlay(true);
    }
  };

  const replayStep = () => {
    seekCue(cueIdx);
  };

  const prevStep = () => {
    if (cueIdx > 0) {
      seekCue(cueIdx - 1);
    }
  };

  const togglePlay = () => {
    const el = videoRef.current;
    if (!el) return;
    if (el.paused) {
      if (isLastCue && isEnded) {
        seekCue(0);
      } else {
        lastPausedCueRef.current = null;
        setIsStepPaused(false);
        void el.play().catch(() => {});
        wakeOverlay();
      }
    } else {
      el.pause();
      setIsStepPaused(true);
      setShowOverlay(true);
    }
  };

  const toggleAutoPause = () => {
    const next = !autoPause;
    setAutoPause(next);
    lastPausedCueRef.current = null;
    try {
      localStorage.setItem(AUTOPAUSE_KEY, String(next));
    } catch {}
  };

  const switchQuality = (q: Quality) => {
    const el = videoRef.current;
    if (el && el.currentTime > 0) resumeRef.current = { time: el.currentTime, playing: !el.paused };
    setQuality(q);
    try {
      localStorage.setItem(QUALITY_KEY, q);
    } catch {}
  };

  const switchSpeed = (s: number) => {
    setSpeed(s);
    if (videoRef.current) videoRef.current.playbackRate = s;
  };

  // Restore position across quality switches
  useEffect(() => {
    const el = videoRef.current;
    const r = resumeRef.current;
    if (!el || !r) return;
    if (r.playing) void el.play().catch(() => {});
    else {
      el.preload = "metadata";
      el.load();
    }
  }, [src]);

  const onLoadedMetadata = () => {
    const el = videoRef.current;
    const r = resumeRef.current;
    if (!el) return;
    el.playbackRate = speed;
    if (r) {
      el.currentTime = r.time;
      if (r.playing) void el.play().catch(() => {});
      resumeRef.current = null;
    }
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={wakeOverlay}
      onTouchStart={wakeOverlay}
      className={`space-y-3 ${
        isFullscreen
          ? "fixed inset-0 z-[99999] flex flex-col justify-center items-center bg-black p-0 m-0 w-screen h-screen overflow-hidden select-none"
          : "relative"
      }`}
    >
      {/* Video Viewport */}
      <div
        className={`relative overflow-hidden group ${
          isFullscreen
            ? "w-full h-full flex items-center justify-center bg-black"
            : "rounded-xl bg-[#0e1116] aspect-video shadow-md"
        }`}
      >
        <video
          ref={videoRef}
          key={src}
          className={`${isFullscreen ? "max-h-full max-w-full object-contain" : "h-full w-full object-contain"}`}
          controls={false}
          playsInline
          preload="none"
          poster={poster}
          onClick={togglePlay}
          onTimeUpdate={onTimeUpdate}
          onSeeked={onTimeUpdate}
          onLoadedMetadata={onLoadedMetadata}
          onPlay={() => {
            setIsPlaying(true);
            setIsStepPaused(false);
            if (videoRef.current) videoRef.current.playbackRate = speed;
            wakeOverlay();
          }}
          onPause={() => {
            setIsPlaying(false);
            setIsStepPaused(true);
            setShowOverlay(true);
          }}
          onEnded={() => {
            setIsPlaying(false);
            setIsEnded(true);
            setIsStepPaused(true);
            setShowOverlay(true);
          }}
          onError={() => setFailed(true)}
        >
          <source src={src} type="video/mp4" />
        </video>

        {/* Big Center Play Button (When Paused) */}
        {!isPlaying && (
          <button
            type="button"
            onClick={togglePlay}
            className="absolute inset-0 m-auto flex h-14 w-14 items-center justify-center rounded-full bg-black/60 text-[#ffffff] backdrop-blur-md border border-[#ffffff]/20 shadow-2xl hover:scale-105 active:scale-95 transition"
            title={km ? "ចាក់វីដេអូ" : "Play"}
          >
            <svg viewBox="0 0 24 24" className="h-6 w-6 ml-0.5 fill-[#ffffff]">
              <path d="M8 5v14l11-7z" />
            </svg>
          </button>
        )}

        {/* Step-pause top pill (When in normal embedded mode) */}
        {!isFullscreen && isStepPaused && !isEnded && autoPause && (
          <div className="pointer-events-none absolute top-3 right-3 flex items-center gap-1.5 rounded-full bg-black/75 backdrop-blur-sm px-2.5 py-1 text-[11px] font-medium text-amber-300 border border-[#ffffff]/15">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span>{km ? `បានផ្អាកត្រង់ជំហានទី ${cueIdx + 1}` : `Paused at step ${cueIdx + 1}`}</span>
          </div>
        )}

        {/* Custom Video Control Bar (Inside the Video Frame) */}
        {!isFullscreen && (
          <div
            className={`absolute bottom-0 left-0 right-0 z-20 flex flex-col justify-end bg-gradient-to-t from-black/80 via-black/40 to-transparent p-3 pt-8 transition-opacity duration-300 ${
              showOverlay || !isPlaying ? "opacity-100" : "opacity-0 pointer-events-none"
            }`}
          >
            {/* Scrubber Timeline */}
            <div className="relative mb-2 flex items-center">
              <input
                type="range"
                min={0}
                max={duration || 100}
                step={0.1}
                value={currentTime}
                onChange={(e) => seekTime(parseFloat(e.target.value))}
                className="h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-[#ffffff]/25 accent-sky-500 transition hover:h-2"
              />
            </div>

            {/* Bottom Row Controls */}
            <div className="flex items-center justify-between text-xs text-[#ffffff]">
              <div className="flex items-center gap-1.5 sm:gap-2">
                {/* Previous Step - Icon Only */}
                <button
                  type="button"
                  onClick={prevStep}
                  disabled={cueIdx === 0}
                  className="rounded p-1 text-[#ffffff] hover:bg-[#ffffff]/20 disabled:opacity-25 transition"
                  title={t("lesson_prev_step")}
                >
                  <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                    <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
                  </svg>
                </button>

                {/* Play / Pause - Icon Only */}
                <button
                  type="button"
                  onClick={togglePlay}
                  className="rounded p-1 hover:bg-[#ffffff]/20 transition text-[#ffffff]"
                  title={isPlaying ? "Pause" : "Play"}
                >
                  {isPlaying ? (
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[#ffffff]">
                      <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[#ffffff]">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  )}
                </button>

                {/* Next Step - Forward Icon Only */}
                <button
                  type="button"
                  onClick={nextStep}
                  disabled={cueIdx === cues.length - 1}
                  className="rounded p-1 text-[#ffffff] hover:bg-[#ffffff]/20 disabled:opacity-25 transition"
                  title={t("lesson_next_step")}
                >
                  <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                    <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
                  </svg>
                </button>

                <span className="ml-1 font-mono text-xs font-semibold text-[#ffffff] tracking-wide">
                  {formatClock(currentTime)} / {formatClock(duration)}
                </span>
              </div>

              <div className="flex items-center gap-1">
                {/* Fullscreen Button - Icon Only */}
                <button
                  type="button"
                  onClick={toggleFullscreen}
                  className="flex h-7 w-7 items-center justify-center rounded text-[#ffffff] hover:bg-[#ffffff]/20 transition"
                  title={km ? "ពង្រីកពេញអេក្រង់" : "Fullscreen"}
                >
                  <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-[#ffffff] stroke-2">
                    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                  </svg>
                </button>

                {/* The 3-Dots (⋮) More Options Button */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowMenu((prev) => !prev);
                    }}
                    className={`flex h-7 w-7 items-center justify-center rounded transition ${
                      showMenu ? "bg-[#ffffff]/30 text-[#ffffff]" : "text-[#ffffff] hover:bg-[#ffffff]/20"
                    }`}
                    title={t("lesson_more_options")}
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[#ffffff]">
                      <circle cx="12" cy="5" r="2" />
                      <circle cx="12" cy="12" r="2" />
                      <circle cx="12" cy="19" r="2" />
                    </svg>
                  </button>

                  {/* Popover Menu */}
                  {showMenu && (
                    <div
                      ref={menuRef}
                      className="absolute bottom-9 right-0 z-50 w-52 rounded-xl border border-[#ffffff]/20 bg-black/95 p-1.5 text-[#ffffff] shadow-2xl backdrop-blur-xl"
                    >
                      {typeof document !== "undefined" && document.pictureInPictureEnabled && (
                        <button
                          type="button"
                          onClick={togglePiP}
                          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs font-semibold text-[#ffffff]/90 hover:bg-[#ffffff]/15 hover:text-[#ffffff] transition"
                        >
                          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-[#ffffff] stroke-2">
                            <path d="M19 11h-8v6h8v-6z" />
                            <path d="M5 21h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                          <span>{t("lesson_pip")}</span>
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={downloadVideo}
                        className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs font-semibold text-[#ffffff]/90 hover:bg-[#ffffff]/15 hover:text-[#ffffff] transition"
                      >
                        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-[#ffffff] stroke-2">
                          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
                        </svg>
                        <span>{t("lesson_download")}</span>
                      </button>

                      <div className="my-1 border-t border-[#ffffff]/15" />

                      <div className="px-3 py-1.5">
                        <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[#ffffff]/60">
                          {t("lesson_speed")}
                        </div>
                        <div className="grid grid-cols-3 gap-1">
                          {SPEEDS.map((s) => (
                            <button
                              key={s}
                              type="button"
                              onClick={() => {
                                switchSpeed(s);
                                setShowMenu(false);
                              }}
                              className={`rounded px-1.5 py-1 text-center text-xs font-semibold transition ${
                                speed === s ? "bg-sky-500 text-[#ffffff]" : "bg-[#ffffff]/10 text-[#ffffff]/80 hover:bg-[#ffffff]/20 hover:text-[#ffffff]"
                              }`}
                            >
                              {s}x
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="px-3 py-1.5">
                        <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[#ffffff]/60">
                          {km ? "កម្រិតរូបភាព" : "Quality"}
                        </div>
                        <div className="grid grid-cols-2 gap-1">
                          {(["hd", "sd"] as const).map((q) => (
                            <button
                              key={q}
                              type="button"
                              onClick={() => {
                                switchQuality(q);
                                setShowMenu(false);
                              }}
                              className={`rounded px-1.5 py-1 text-center text-xs font-semibold transition ${
                                quality === q ? "bg-sky-500 text-[#ffffff]" : "bg-[#ffffff]/10 text-[#ffffff]/80 hover:bg-[#ffffff]/20 hover:text-[#ffffff]"
                              }`}
                            >
                              {q === "hd" ? t("lesson_video_hd") : t("lesson_video_data_saver")}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ======================================================== */}
        {/* FULLSCREEN MODE: FLOATING GLASSMORPHIC HUD (OPTION 1)   */}
        {/* ======================================================== */}
        {isFullscreen && (
          <>
            {/* Top Bar Header */}
            <div
              className={`absolute top-4 left-4 right-4 flex items-center justify-between z-50 transition-opacity duration-300 ${
                showOverlay || !isPlaying ? "opacity-100" : "opacity-0 pointer-events-none"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-black/70 backdrop-blur-md px-3.5 py-1 text-xs font-bold text-[#ffffff] border border-[#ffffff]/15">
                  {km ? `ជំហានទី ${cueIdx + 1} / ${cues.length}` : `Step ${cueIdx + 1} of ${cues.length}`}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {/* Speed buttons */}
                <div className="flex rounded-lg bg-black/70 backdrop-blur-md border border-[#ffffff]/15 p-0.5 text-xs text-[#ffffff]">
                  {SPEEDS.map((s) => (
                    <button
                      key={s}
                      onClick={() => switchSpeed(s)}
                      className={`rounded px-2.5 py-0.5 transition ${
                        speed === s ? "bg-[#ffffff]/25 font-bold text-[#ffffff] shadow-sm" : "text-[#ffffff]/70 hover:text-[#ffffff]"
                      }`}
                    >
                      {s}x
                    </button>
                  ))}
                </div>

                {/* Exit Fullscreen - Icon Only */}
                <button
                  type="button"
                  onClick={toggleFullscreen}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-black/70 text-[#ffffff] backdrop-blur-md border border-[#ffffff]/15 hover:bg-[#ffffff]/20 transition"
                  title={km ? "ចេញពីពេញអេក្រង់" : "Exit Fullscreen"}
                >
                  <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-[#ffffff] stroke-2 stroke-linecap-round stroke-linejoin-round">
                    <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Bottom Floating Subtitle HUD with Full Navigation */}
            <div className="absolute bottom-6 left-4 right-4 sm:left-1/2 sm:-translate-x-1/2 sm:w-[640px] z-50 transition-all duration-300">
              <div className="rounded-2xl border border-[#ffffff]/20 bg-black/85 backdrop-blur-2xl p-4 text-[#ffffff] shadow-2xl transition-all duration-300">
                {/* Active Caption with KaTeX — ALWAYS VISIBLE IN FULLSCREEN */}
                <div className="flex items-start gap-3">
                  <span className="shrink-0 flex items-center justify-center h-6 w-6 rounded-full bg-sky-500 text-[#ffffff] text-xs font-bold shadow-md">
                    {cueIdx + 1}
                  </span>
                  <div className="min-h-[2.25rem] flex-1 text-sm sm:text-base leading-relaxed text-[#ffffff] font-medium font-sans [&_.katex]:text-[#ffffff] [&_.katex]:font-normal">
                    {cue && <MathText text={km ? cue.text_km : cue.text_en} />}
                  </div>
                </div>

                {/* Collapsible Scrubber & Action Controls — Automatically hides during playback */}
                <div
                  className={`transition-all duration-300 ${
                    showOverlay || !isPlaying
                      ? "max-h-44 opacity-100 mt-2.5 pt-2 border-t border-[#ffffff]/15 overflow-visible"
                      : "max-h-0 opacity-0 mt-0 pt-0 border-t-0 pointer-events-none overflow-hidden"
                  }`}
                >
                  {/* Scrubber within Fullscreen HUD */}
                  <div className="mb-2 flex items-center gap-2 text-xs text-[#ffffff]/90">
                    <span className="font-mono text-[#ffffff]">{formatClock(currentTime)}</span>
                    <input
                      type="range"
                      min={0}
                      max={duration || 100}
                      step={0.1}
                      value={currentTime}
                      onChange={(e) => seekTime(parseFloat(e.target.value))}
                      className="h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-[#ffffff]/20 accent-sky-400"
                    />
                    <span className="font-mono text-[#ffffff]">{formatClock(duration)}</span>
                  </div>

                  {/* Action Bar inside Fullscreen */}
                  <div className="flex items-center justify-between text-xs">
                    {/* Step Control Icons */}
                    <div className="flex items-center gap-1.5 sm:gap-2">
                      {/* Previous Step - Icon Only */}
                      <button
                        type="button"
                        onClick={prevStep}
                        disabled={cueIdx === 0}
                        className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#ffffff]/15 hover:bg-[#ffffff]/25 text-[#ffffff] disabled:opacity-25 transition"
                        title={t("lesson_prev_step")}
                      >
                        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                          <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
                        </svg>
                      </button>

                      {/* Replay Step - Icon Only */}
                      <button
                        type="button"
                        onClick={replayStep}
                        className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#ffffff]/15 hover:bg-[#ffffff]/25 text-[#ffffff] transition"
                        title={t("lesson_replay_step")}
                      >
                        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-2">
                          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                          <path d="M3 3v5h5" />
                        </svg>
                      </button>

                      {/* Play / Pause - Icon Only */}
                      <button
                        type="button"
                        onClick={togglePlay}
                        className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#ffffff]/15 hover:bg-[#ffffff]/25 text-[#ffffff] transition"
                        title={isPlaying ? "Pause" : "Play"}
                      >
                        {isPlaying ? (
                          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                          </svg>
                        ) : (
                          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                            <path d="M8 5v14l11-7z" />
                          </svg>
                        )}
                      </button>

                      {/* Next Step - Forward Icon Only */}
                      {!isLastCue ? (
                        <button
                          type="button"
                          onClick={nextStep}
                          className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500 hover:bg-sky-400 text-[#ffffff] shadow-md transition"
                          title={t("lesson_next_step")}
                        >
                          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                            <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
                          </svg>
                        </button>
                      ) : (
                        onTrySimilar && (
                          <button
                            type="button"
                            onClick={() => {
                              void toggleFullscreen();
                              onTrySimilar();
                            }}
                            className="flex items-center gap-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 px-3 py-1.5 text-xs font-bold text-[#ffffff] shadow-md transition animate-bounce"
                          >
                            <span>✍️</span>
                            <span>{t("lesson_try_similar")}</span>
                          </button>
                        )
                      )}
                    </div>

                    {/* Auto-Stop / Continuous Toggle Switch */}
                    <div className="flex items-center rounded-lg bg-black/60 p-0.5 border border-[#ffffff]/15 text-xs">
                      <button
                        type="button"
                        onClick={() => {
                          setAutoPause(true);
                          try { localStorage.setItem(AUTOPAUSE_KEY, "true"); } catch {}
                        }}
                        className={`flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold transition ${
                          autoPause
                            ? "bg-amber-500 text-[#ffffff] shadow-sm"
                            : "text-[#ffffff]/60 hover:text-[#ffffff]"
                        }`}
                        title={km ? "ផ្អាកដោយស្វ័យប្រវត្តិតាមជំហាន" : "Auto-pause at step end"}
                      >
                        <svg viewBox="0 0 24 24" className="h-3 w-3 fill-current">
                          <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                        </svg>
                        <span className="hidden sm:inline">{km ? "ឈប់តាមជំហាន" : "Auto-stop"}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setAutoPause(false);
                          try { localStorage.setItem(AUTOPAUSE_KEY, "false"); } catch {}
                        }}
                        className={`flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold transition ${
                          !autoPause
                            ? "bg-sky-500 text-[#ffffff] shadow-sm"
                            : "text-[#ffffff]/60 hover:text-[#ffffff]"
                        }`}
                        title={km ? "ចាក់បន្តរហូតចប់" : "Play continuously"}
                      >
                        <svg viewBox="0 0 24 24" className="h-3 w-3 fill-current">
                          <path d="M8 5v14l11-7z" />
                        </svg>
                        <span className="hidden sm:inline">{km ? "ចាក់បន្ត" : "Auto-play"}</span>
                      </button>
                    </div>

                    {/* Right side: 3-Dots Menu & Fullscreen Toggle */}
                    <div className="flex items-center gap-1.5">
                      {/* The 3-Dots (⋮) More Options Button (In Bottom Bar) */}
                      <div className="relative">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setShowMenu((prev) => !prev);
                          }}
                          className={`flex h-8 w-8 items-center justify-center rounded-lg transition ${
                            showMenu ? "bg-[#ffffff]/30 text-[#ffffff]" : "text-[#ffffff] hover:bg-[#ffffff]/20"
                          }`}
                          title={t("lesson_more_options")}
                        >
                          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[#ffffff]">
                            <circle cx="12" cy="5" r="2" />
                            <circle cx="12" cy="12" r="2" />
                            <circle cx="12" cy="19" r="2" />
                          </svg>
                        </button>

                        {/* Popover Menu in Fullscreen */}
                        {showMenu && (
                          <div
                            ref={menuRef}
                            className="absolute bottom-10 right-0 z-50 w-52 rounded-xl border border-[#ffffff]/20 bg-black/95 p-1.5 text-[#ffffff] shadow-2xl backdrop-blur-xl"
                          >
                            {typeof document !== "undefined" && document.pictureInPictureEnabled && (
                              <button
                                type="button"
                                onClick={togglePiP}
                                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs font-semibold text-[#ffffff]/90 hover:bg-[#ffffff]/15 hover:text-[#ffffff] transition"
                              >
                                <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-[#ffffff] stroke-2">
                                  <path d="M19 11h-8v6h8v-6z" />
                                  <path d="M5 21h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                </svg>
                                <span>{t("lesson_pip")}</span>
                              </button>
                            )}

                            <button
                              type="button"
                              onClick={downloadVideo}
                              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs font-semibold text-[#ffffff]/90 hover:bg-[#ffffff]/15 hover:text-[#ffffff] transition"
                            >
                              <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-[#ffffff] stroke-2">
                                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
                              </svg>
                              <span>{t("lesson_download")}</span>
                            </button>

                            <div className="my-1 border-t border-[#ffffff]/15" />

                            <div className="px-3 py-1.5">
                              <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[#ffffff]/60">
                                {t("lesson_speed")}
                              </div>
                              <div className="grid grid-cols-3 gap-1">
                                {SPEEDS.map((s) => (
                                  <button
                                    key={s}
                                    type="button"
                                    onClick={() => {
                                      switchSpeed(s);
                                      setShowMenu(false);
                                    }}
                                    className={`rounded px-1.5 py-1 text-center text-xs font-semibold transition ${
                                      speed === s ? "bg-sky-500 text-[#ffffff]" : "bg-[#ffffff]/10 text-[#ffffff]/80 hover:bg-[#ffffff]/20 hover:text-[#ffffff]"
                                    }`}
                                  >
                                    {s}x
                                  </button>
                                ))}
                              </div>
                            </div>

                            <div className="px-3 py-1.5">
                              <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[#ffffff]/60">
                                {km ? "កម្រិតរូបភាព" : "Quality"}
                              </div>
                              <div className="grid grid-cols-2 gap-1">
                                {(["hd", "sd"] as const).map((q) => (
                                  <button
                                    key={q}
                                    type="button"
                                    onClick={() => {
                                      switchQuality(q);
                                      setShowMenu(false);
                                    }}
                                    className={`rounded px-1.5 py-1 text-center text-xs font-semibold transition ${
                                      quality === q ? "bg-sky-500 text-[#ffffff]" : "bg-[#ffffff]/10 text-[#ffffff]/80 hover:bg-[#ffffff]/20 hover:text-[#ffffff]"
                                    }`}
                                  >
                                    {q === "hd" ? t("lesson_video_hd") : t("lesson_video_data_saver")}
                                  </button>
                                ))}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Exit Fullscreen - Icon Only */}
                      <button
                        type="button"
                        onClick={toggleFullscreen}
                        className="flex h-8 w-8 items-center justify-center rounded-lg text-[#ffffff] hover:bg-[#ffffff]/20 transition"
                        title={km ? "ចេញពីពេញអេក្រង់" : "Exit Fullscreen"}
                      >
                        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-[#ffffff] stroke-2 stroke-linecap-round stroke-linejoin-round">
                          <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ======================================================== */}
      {/* NORMAL EMBEDDED VIEW (OUTSIDE FULLSCREEN)               */}
      {/* ======================================================== */}
      {!isFullscreen && (
        <>
          {failed ? (
            <p className="text-sm text-red-600">{t("lesson_video_error")}</p>
          ) : (
            <div
              id="lesson-caption"
              aria-live="polite"
              className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-slate-900 shadow-sm transition-colors [&_.katex]:text-slate-900"
            >
              {/* Active Step Caption */}
              <div className="flex items-start gap-3">
                <span className="shrink-0 flex items-center justify-center h-6 w-6 rounded-full bg-sky-500 text-[#ffffff] text-xs font-bold shadow-xs">
                  {cueIdx + 1}
                </span>
                <div className="min-h-[3.25rem] flex-1 text-[15px] font-medium leading-relaxed text-slate-900">
                  {cue && <MathText text={km ? cue.text_km : cue.text_en} />}
                </div>
              </div>

              {/* Step Action Bar - Clean Icon-Only Navigation */}
              <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-200 pt-2.5 text-xs">
                <div className="flex items-center gap-1.5">
                  {/* Previous Step - Icon Only */}
                  <button
                    type="button"
                    onClick={prevStep}
                    disabled={cueIdx === 0}
                    className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-200/80 hover:bg-slate-300 text-slate-700 disabled:opacity-25 transition font-medium"
                    title={t("lesson_prev_step")}
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                      <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
                    </svg>
                  </button>

                  {/* Replay Step - Icon Only */}
                  <button
                    type="button"
                    onClick={replayStep}
                    className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-200/80 hover:bg-slate-300 text-slate-700 transition font-medium"
                    title={t("lesson_replay_step")}
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-2">
                      <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  {!isLastCue ? (
                    /* Next Step - Forward Icon Only */
                    <button
                      type="button"
                      onClick={nextStep}
                      className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500 hover:bg-sky-400 text-[#ffffff] shadow-sm transition"
                      title={t("lesson_next_step")}
                    >
                      <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                        <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
                      </svg>
                    </button>
                  ) : (
                    onTrySimilar && (
                      <button
                        type="button"
                        onClick={onTrySimilar}
                        className="flex items-center gap-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-[#ffffff] font-bold px-3 py-1.5 shadow-sm transition animate-bounce"
                      >
                        <span>✍️</span>
                        <span>{t("lesson_try_similar")}</span>
                      </button>
                    )
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Completion Card: Try Similar Problem on Canvas */}
          {isEnded && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 shadow-sm text-slate-900 transition-colors">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-lg">🎓</span>
                    <h4 className="font-bold text-sm text-slate-900">{t("lesson_completed_title")}</h4>
                  </div>
                  <p className="mt-1 text-xs text-slate-600 leading-relaxed">{t("lesson_completed_desc")}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => seekCue(0)}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition"
                  >
                    <span>↺</span> {t("lesson_replay_all")}
                  </button>
                  {onTrySimilar && (
                    <button
                      type="button"
                      onClick={onTrySimilar}
                      className="flex items-center gap-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 px-4 py-1.5 text-xs font-bold text-[#ffffff] shadow-sm transition"
                    >
                      <span>✍️</span>
                      <span>{t("lesson_try_similar")}</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Player Toolbar: Step numbers, Auto-pause Toggle, Speed, Quality */}
          <div className="flex flex-wrap items-center justify-between gap-2.5 pt-1">
            {/* Step Numbers */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t("lesson_steps")}
              </span>
              {cues.map((c, i) => (
                <button
                  key={c.id}
                  onClick={() => seekCue(i)}
                  title={(km ? c.text_km : c.text_en).replace(/\$/g, "")}
                  className={`h-7 min-w-7 rounded-md px-2 text-xs font-semibold transition stylus:h-9 stylus:min-w-9 ${
                    i === cueIdx
                      ? "bg-sky-500 text-[#ffffff] shadow-sm"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {i + 1}
                </button>
              ))}
            </div>

            {/* Right side controls: Auto-stop / Continuous Toggle, Speed, Quality */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Auto-stop / Continuous Segmented Toggle Switch */}
              <div className="flex items-center rounded-lg bg-slate-100 p-0.5 text-xs font-medium border border-slate-200">
                <button
                  type="button"
                  onClick={() => {
                    setAutoPause(true);
                    try { localStorage.setItem(AUTOPAUSE_KEY, "true"); } catch {}
                  }}
                  className={`flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold transition ${
                    autoPause
                      ? "bg-amber-500 text-[#ffffff] shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                  title={km ? "ផ្អាកដោយស្វ័យប្រវត្តិតាមជំហាន" : "Auto-pause at step end"}
                >
                  <svg viewBox="0 0 24 24" className="h-3 w-3 fill-current">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                  </svg>
                  <span>{km ? "ឈប់តាមជំហាន" : "Auto-stop"}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAutoPause(false);
                    try { localStorage.setItem(AUTOPAUSE_KEY, "false"); } catch {}
                  }}
                  className={`flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold transition ${
                    !autoPause
                      ? "bg-sky-500 text-[#ffffff] shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                  title={km ? "ចាក់បន្តរហូតចប់" : "Play continuously"}
                >
                  <svg viewBox="0 0 24 24" className="h-3 w-3 fill-current">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                  <span>{km ? "ចាក់បន្ត" : "Continuous"}</span>
                </button>
              </div>

              {/* Playback Speed */}
              <div className="flex rounded-lg bg-slate-100 p-0.5 text-xs font-medium border border-slate-200">
                {SPEEDS.map((s) => (
                  <button
                    key={s}
                    onClick={() => switchSpeed(s)}
                    className={`rounded-md px-2 py-1 transition ${
                      speed === s
                        ? "bg-white text-slate-900 shadow-sm font-semibold"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    {s}x
                  </button>
                ))}
              </div>

              {/* Quality */}
              <div className="flex rounded-lg bg-slate-100 p-0.5 text-xs font-medium border border-slate-200">
                {(["hd", "sd"] as const).map((q) => (
                  <button
                    key={q}
                    onClick={() => switchQuality(q)}
                    className={`rounded-md px-2.5 py-1 transition ${
                      quality === q
                        ? "bg-white text-slate-900 shadow-sm font-semibold"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    {q === "hd" ? t("lesson_video_hd") : t("lesson_video_data_saver")}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
