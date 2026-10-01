"""Factoring a 0/0 form: the graph is a line with a hole; cancelling the common
factor recovers the line and fills the hole."""
from manim import Create, Dot, FadeOut, ReplacementTransform, Transform, VGroup

from common.limit_kit import LimitScene, safe
from common.style import CURVE_ALT, LIMIT


@safe
def f(x):
    return (x**2 - 9) / (x - 3)


class Lesson(LimitScene):
    lesson_id = "factoring_0_0"

    def construct(self):
        self.check("(x**2 - 9)/(x - 3)", 3, 6)

        self.cue("problem")
        prob = self.problem(r"\lim_{x \to 3} \frac{x^2 - 9}{x - 3}")

        self.cue("substitute")
        sub = self.column([r"\frac{3^2 - 9}{3 - 3}", r"= \frac{0}{0}"], top=2.5)
        self.derive(sub)
        sub[1].set_color("#fc6255")

        self.cue("graph")
        ax = self.axes([0, 5, 1], [0, 9, 1], x_numbers=[1, 2, 3, 4], y_numbers=[2, 4, 6, 8])
        curve = self.graph(ax, f, discontinuities=[3])
        hole = self.hole(ax, 3, 6)
        self.play(Create(ax), run_time=1.0)
        self.play(Create(curve), run_time=1.8)
        self.add(hole)
        self.wait(1.0)

        self.cue("approach")
        h, riders = self.approach(ax, f, 3, h_start=1.8, h_end=0.15, run_time=4.0)

        self.cue("zoom")
        self.zoom_to(VGroup(ax, curve), ax.c2p(3, 6), factor=6, hide=[prob, *sub])
        self.play(h.animate.set_value(0.004), run_time=3.0)
        self.wait(0.5)
        self.zoom_back()

        self.cue("factor")
        self.clear(riders, *sub)
        alg = self.column([
            r"\frac{x^2 - 9}{x - 3}",
            r"= \frac{(x - 3)(x + 3)}{x - 3}",
            r"= x + 3",
        ], top=2.5)
        self.derive(alg[:2])

        self.cue("cancel")
        self.play(ReplacementTransform(alg[1].copy(), alg[2]), run_time=1.3)
        line = self.graph(ax, lambda x: x + 3, color=CURVE_ALT, width=5)
        filled = Dot(ax.c2p(3, 6), color=CURVE_ALT, radius=0.08)
        self.play(Create(line), run_time=1.5)
        self.play(FadeOut(hole), Transform(curve, line), Create(filled), run_time=1.0)

        self.cue("answer")
        ans = self.column([r"\lim_{x \to 3} (x + 3) = 6"], top=alg[2].get_bottom()[1] - 0.6)[0]
        guide = self.guide(ax, 3, 6, "6")
        self.play(Create(guide), ReplacementTransform(alg[2].copy(), ans), run_time=1.2)
        filled.set_color(LIMIT)
        self.box(ans)
        self.end_cues()
