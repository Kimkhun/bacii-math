# Sounds & streaks (`web/src/lib/sounds.ts`)

Synthesized grade feedback — pure Web Audio, **no asset files**. Correct marks
play a bright "ding" whose pitch rises one semitone per consecutive correct
mark (a kill-streak combo); wrong marks play a low thud.

## Public API

| Function | Purpose |
|---|---|
| `getStreak()` | Consecutive-correct counter from `localStorage["bacii_streak"]` |
| `updateStreak(correct)` | `+1` on correct, reset to 0 on wrong; persists; returns new value |
| `playMarkSound(correct, step)` | One line-mark: correct → ding at `step` semitones; wrong → thud |
| `playGradeSound(correct)` | Single verdict (typed answers / no line marks): ding at current streak, or thud |

## Pitch math

- `base = 440 · 2^(min(step, 12) / 12)` — one semitone per step, capped at an
  octave so it stays pleasant.
- The ding is two oscillators (main + octave shimmer), plus a triangle grace
  note at `step ≥ 3`.
- The thud is a falling sawtooth + sine at ~165→110 Hz.

## When each sound fires (practice page `check()`)

- **Correct answer (SymPy-verified):** EVERY checked line dings, pitch rising
  from `streak − 1 + i` — intermediate verdicts are ignored on purpose, because
  the checker may not confirm alternative-path lines; the pitch must never
  depend on them. Final victory ping lands on the stamp.
- **Wrong answer:** correct lines ding (rising from 0); only the FIRST wrong
  line thuds (no thud-stacks); the rest are silent.
- **No line marks** (typed answers, no boxes): single `playGradeSound`.
- Timing: each sound is scheduled with `setTimeout(i · MARK_STAGGER_MS)`
  (1000 ms) to land exactly when the corresponding line pops in (`.mark-pop`
  animation).

## Implementation notes

- `AudioContext` is created lazily on first play and resumed if suspended
  (browser autoplay policy — grading is a user gesture, so it works).
- The streak lives in `localStorage`, so it persists across sessions.
- No backend involvement: streaks and sounds are entirely client-side.