// Synthesized grade feedback sounds (Web Audio, no asset files).
// Correct line-marks play a bright "ding" whose pitch rises one semitone per
// consecutive correct mark (capped at an octave), like a kill-streak combo.
// Wrong marks play a short low thud.

const STREAK_KEY = "bacii_streak";

let ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
  }
  if (ctx.state === "suspended") void ctx.resume();
  return ctx;
}

function tone(
  ac: AudioContext,
  freq: number,
  start: number,
  duration: number,
  type: OscillatorType = "sine",
  gainPeak = 0.25,
  endFreq?: number
) {
  const osc = ac.createOscillator();
  const gain = ac.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, start);
  if (endFreq !== undefined) osc.frequency.exponentialRampToValueAtTime(endFreq, start + duration);
  gain.gain.setValueAtTime(0, start);
  gain.gain.linearRampToValueAtTime(gainPeak, start + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  osc.connect(gain);
  gain.connect(ac.destination);
  osc.start(start);
  osc.stop(start + duration + 0.05);
}

// One correct mark: bright "kill" ping at `step` semitones above base (capped
// at 12 = an octave), plus octave shimmer and a grace note from step 3 on.
function playCorrect(ac: AudioContext, step: number) {
  const now = ac.currentTime;
  const steps = Math.min(Math.max(step, 0), 12);
  const base = 440 * Math.pow(2, steps / 12);
  tone(ac, base, now, 0.35, "sine", 0.22);
  tone(ac, base * 2, now, 0.28, "sine", 0.08);
  if (steps >= 3) {
    tone(ac, base / 2, now, 0.18, "triangle", 0.1, base * 0.75);
  }
}

function playWrong(ac: AudioContext) {
  const now = ac.currentTime;
  tone(ac, 165, now, 0.28, "sawtooth", 0.12, 110);
  tone(ac, 82, now + 0.05, 0.32, "sine", 0.15, 60);
}

export function getStreak(): number {
  if (typeof window === "undefined") return 0;
  const raw = parseInt(localStorage.getItem(STREAK_KEY) ?? "0", 10);
  return Number.isFinite(raw) && raw > 0 ? raw : 0;
}

export function updateStreak(correct: boolean): number {
  if (typeof window === "undefined") return 0;
  const next = correct ? getStreak() + 1 : 0;
  localStorage.setItem(STREAK_KEY, String(next));
  return next;
}

// Play a sound for one line-mark: correct -> rising ping at the given semitone
// step (feed it the running combo counter), wrong -> low thud.
export function playMarkSound(correct: boolean, step: number): void {
  const ac = getCtx();
  if (!ac) return;
  if (correct) playCorrect(ac, step);
  else playWrong(ac);
}

// Convenience for a single verdict (e.g. typed answers, no line marks):
// correct -> ping at the current streak, wrong -> thud.
export function playGradeSound(correct: boolean): void {
  const ac = getCtx();
  if (!ac) return;
  if (correct) playCorrect(ac, getStreak());
  else playWrong(ac);
}