"""x ln x -> 0 as x -> 0+: the factor x shrinks faster than ln x blows up."""
import math

from manim import DOWN, LEFT, RIGHT, Create, DecimalNumber, FadeIn, MathTex, VGroup, Write

from common.limit_kit import LimitScene, safe
from common.style import CURVE_ALT, LIMIT, POINT, WARN


def f(x):
    return x * math.log(x)


class Lesson(LimitScene):
    lesson_id = "log_limit_zero"

    def construct(self):
        self.check("x*log(x)", 0, 0, side="+")

        self.cue("problem")
        prob = self.problem(r"\lim_{x \to 0^+} x \ln x")

        self.cue("form")
        self.warn(r"\to 0 \cdot (-\infty)", prob, direction=RIGHT)

        self.cue("graph")
        ax = self.axes([0, 1.5, 0.25], [-0.5, 0.75, 0.25], x_numbers=[1])
        curve = self.graph(ax, safe(f), x_range=[0.0005, 1.5])
        hole = self.hole(ax, 0, 0)
        self.play(Create(ax), run_time=1.0)
        self.play(Create(curve), run_time=1.8)
        self.add(hole)

        self.cue("race")
        h, rider = self.approach(ax, safe(f), 0, h_start=1.3, sides=(1,), decimals=4, animate=False)
        table = self.hud(lambda: VGroup(
            VGroup(MathTex("x =").scale(0.8),
                   DecimalNumber(h.get_value(), num_decimal_places=4, font_size=36)).arrange(RIGHT, buff=0.15),
            VGroup(MathTex(r"\ln x =").scale(0.8),
                   DecimalNumber(math.log(h.get_value()), num_decimal_places=2, font_size=36, color=WARN)
                   ).arrange(RIGHT, buff=0.15),
            VGroup(MathTex(r"x \ln x =").scale(0.8),
                   DecimalNumber(f(h.get_value()), num_decimal_places=4, font_size=36, color=POINT)
                   ).arrange(RIGHT, buff=0.15),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.25), corner=RIGHT, buff=0.8)
        self.play(FadeIn(table), run_time=0.6)
        self.play(h.animate.set_value(0.0005), run_time=6.0)

        self.cue("rule")
        rule = self.column([r"x^p \ln x \xrightarrow[x \to 0^+]{} 0 \quad (p > 0)"], top=-1.3)[0]
        rule.set_color(CURVE_ALT)
        self.play(Write(rule), run_time=1.4)

        self.cue("answer")
        ans = self.column([r"\lim_{x \to 0^+} x \ln x = 0"], top=rule.get_bottom()[1] - 0.4)[0]
        self.play(Write(ans), run_time=1.2)
        self.box(ans, color=LIMIT)
        self.end_cues()

