"""``CaptionedScene``: a Manim scene whose timeline is split into caption cues.

The captions a student reads are not drawn into the video — they live in the
topic's ``backend/engine/topics/<topic>/data/animations.json`` (bilingual, edited
without re-rendering) and the web shows them under the player. The scene only
marks *when* each cue starts::

    self.cue("approach")       # cue "approach" starts now
    ...animations...
    self.cue("cancel")         # previous cue ends, next begins
    ...
    self.end_cues()            # closes the last cue

Each cue is held on screen at least as long as its longest caption takes to
read (see ``reading_time``): if the animations between two ``cue`` calls are
shorter, ``cue`` pads with ``self.wait``. Timings are dumped to ``$CUES_OUT``
when the scene ends, and ``animations/render.py`` merges them back into
``animations.json``.
"""
import json
import os
import re
from pathlib import Path

from manim import MovingCameraScene

from .style import BACKGROUND

REPO = Path(os.environ.get("BACII_REPO", Path(__file__).resolve().parents[2]))


#: Formula tutorials are not tied to one topic's lessons: they are keyed by
#: formula id (the tags of ``engine/formulas.py``) and live in one registry.
FORMULAS = "formulas"


def animations_path(topic: str) -> Path:
    if topic == FORMULAS:
        return REPO / "backend" / "engine" / "data" / "formula_animations.json"
    return REPO / "backend" / "engine" / "topics" / topic / "data" / "animations.json"


def lessons_path(topic: str) -> Path:
    return REPO / "backend" / "engine" / "topics" / topic / "data" / "lessons.json"


def load_lesson(topic: str, lesson_id: str) -> dict:
    with open(lessons_path(topic), encoding="utf-8") as fh:
        return json.load(fh)[lesson_id]


def _visible_len(text: str) -> float:
    """Characters a reader actually has to read: inline math counts half (it is
    short to read relative to its LaTeX source)."""
    math = re.findall(r"\$[^$]*\$", text)
    prose = re.sub(r"\$[^$]*\$", "", text)
    return len(prose) + 0.5 * sum(len(m) for m in math)


def reading_time(cue: dict) -> float:
    """Seconds a cue must stay up: the slower of the two languages, at a
    comfortable pace for a student also watching the animation (English ~15
    chars/s; Khmer script is denser per character, ~11/s)."""
    en = _visible_len(cue.get("text_en", "")) / 15
    km = _visible_len(cue.get("text_km", "")) / 11
    return max(2.5, en, km) + 0.6


class CaptionedScene(MovingCameraScene):
    topic: str = ""
    lesson_id: str = ""

    def setup(self):
        super().setup()
        self.camera.background_color = BACKGROUND
        with open(animations_path(self.topic), encoding="utf-8") as fh:
            authored = json.load(fh)[self.lesson_id]["cues"]
        self._authored = {c["id"]: c for c in authored}
        self._timeline: list[dict] = []
        self._open: dict | None = None

    @property
    def lesson(self) -> dict:
        return load_lesson(self.topic, self.lesson_id)

    @property
    def now(self) -> float:
        return self.renderer.time

    def _close(self):
        if self._open is None:
            return
        need = reading_time(self._authored[self._open["id"]])
        elapsed = self.now - self._open["start"]
        if elapsed < need:
            self.wait(need - elapsed)
        self._open = None

    def cue(self, cue_id: str):
        if cue_id not in self._authored:
            raise KeyError(f"cue {cue_id!r} is not authored in {animations_path(self.topic)}")
        self._close()
        self._open = {"id": cue_id, "start": round(self.now, 3)}
        self._timeline.append(self._open)

    def end_cues(self, tail: float = 1.0):
        self._close()
        self.wait(tail)

    def tear_down(self):
        super().tear_down()
        out = os.environ.get("CUES_OUT")
        if out:
            Path(out).write_text(
                json.dumps({"cues": self._timeline, "duration": round(self.now, 3)}),
                encoding="utf-8",
            )
