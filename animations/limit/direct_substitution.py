"""Direct substitution: a continuous curve has no gap, so the limit is f(a)."""
from manim import Create, Dot, FadeIn, FadeOut

from common.limit_kit import LimitScene
from common.style import LIMIT


def f(x):
    return x**2 + 3 * x - 1


class Lesson(LimitScene):
    lesson_id = "direct_substitution"

    def construct(self):
        self.check("x**2 + 3*x - 1", 2, 9)

        self.cue("problem")
        self.problem(r"\lim_{x \to 2} \left(x^2 + 3x - 1\right)")

        self.cue("graph")
        ax = self.axes([-1, 4, 1], [-5, 30, 5], x_numbers=[1, 2, 3], y_numbers=[20])
        curve = self.graph(ax, f)
        self.play(Create(ax), run_time=1.2)
        self.play(Create(curve), run_time=2.0)

        self.cue("approach")
        _, riders = self.approach(ax, f, 2, h_start=1.6, h_end=0.01, run_time=4.5)

        self.cue("match")
        point = Dot(ax.c2p(2, 9), color=LIMIT, radius=0.09)
        guide = self.guide(ax, 2, 9, "9")
        self.play(FadeOut(riders), FadeIn(point, scale=2), Create(guide), run_time=1.2)

        self.cue("substitute")
        lines = self.column([
            r"\lim_{x \to 2}\left(x^2 + 3x - 1\right)",
            r"= 2^2 + 3 \cdot 2 - 1",
            r"= 9",
        ], top=2.3)
        self.derive(lines)

        self.cue("answer")
        self.box(lines[-1])
        self.end_cues()
