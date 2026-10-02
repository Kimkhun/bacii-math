"""(e^u - 1)/u -> 1 as the slope of a secant of e^u turning into the tangent
at (0, 1); then (e^3x - 1)/(e^5x - 1) by balancing each bracket."""
import math

from manim import (
    LEFT, RIGHT, Create, DecimalNumber, Dot, FadeIn, Line, MathTex, ValueTracker, VGroup, Write,
    always_redraw,
)

from common.limit_kit import LimitScene, safe
from common.style import AXIS, LIMIT, POINT

X0, X1, Y1 = -1.5, 1.6, 5.0


def slope(u):
    return (math.exp(u) - 1) / u


class Lesson(LimitScene):
    lesson_id = "exponential_standard_limit"

    def construct(self):
        self.check("(exp(x) - 1)/x", 0, 1)
        self.check("(exp(3*x) - 1)/(exp(5*x) - 1)", 0, "3/5")

        self.cue("problem")
        prob = self.problem(r"\lim_{x \to 0} \frac{e^{3x} - 1}{e^{5x} - 1}")
        self.warn(r"\to \frac{0}{0}", prob, direction=RIGHT)

        self.cue("secant")
        ax = self.axes([X0, X1, 0.5], [0, Y1, 1], x_numbers=[-1, 1], y_numbers=[1, 2, 3, 4])
        curve = self.graph(ax, math.exp, x_range=[X0, math.log(Y1)])
        e_label = MathTex("e^u", color=curve.get_color()).scale(0.9).next_to(ax.c2p(1.5, 4.5), LEFT)
        self.play(Create(ax), run_time=1.0)
        self.play(Create(curve), FadeIn(e_label), run_time=1.5)

        u = ValueTracker(1.3)

        def secant():
            m = slope(u.get_value())
            lo, hi = max(X0, -1 / m), min(X1, (Y1 - 1) / m)
            return Line(ax.c2p(lo, 1 + m * lo), ax.c2p(hi, 1 + m * hi), color=POINT, stroke_width=4)

        line = always_redraw(secant)
        q = Dot(ax.c2p(0, 1), color=AXIS, radius=0.07)
        p = always_redraw(lambda: Dot(ax.c2p(u.get_value(), math.exp(u.get_value())), color=POINT, radius=0.08))
        readout = self.hud(lambda: VGroup(
            MathTex(r"u =").scale(0.8),
            DecimalNumber(u.get_value(), num_decimal_places=3, font_size=36, color=POINT),
            MathTex(r"\quad \frac{e^u - 1}{u} =").scale(0.8),
            DecimalNumber(slope(u.get_value()), num_decimal_places=3, font_size=36, color=LIMIT),
        ).arrange(RIGHT, buff=0.15), corner=RIGHT, buff=0.4)
        self.play(FadeIn(q), FadeIn(p), Create(line), FadeIn(readout), run_time=1.2)
        self.play(u.animate.set_value(0.6), run_time=2.0)

        self.cue("tangent")
        self.play(u.animate.set_value(0.01), run_time=3.0)
        self.play(u.animate.set_value(-1.2), run_time=1.5)
        self.play(u.animate.set_value(-0.01), run_time=2.5)
        tangent = Line(ax.c2p(X0, 1 + X0), ax.c2p(X1, 1 + X1), color=LIMIT, stroke_width=3)
        self.play(Create(tangent), run_time=1.0)

        self.cue("balance")
        self.clear(ax, curve, e_label, line, p, q, readout, tangent)
        ax2 = self.axes([-1.5, 1.5, 0.5], [0, 1.2, 0.2], x_numbers=[-1, 1])
        f = safe(lambda x: (math.exp(3 * x) - 1) / (math.exp(5 * x) - 1))
        curve2 = self.graph(ax2, f, discontinuities=[0])
        hole = self.hole(ax2, 0, 0.6)
        self.play(Create(ax2), Create(curve2), run_time=1.5)
        self.add(hole)
        alg = self.column([
            r"\frac{e^{3x} - 1}{e^{5x} - 1} = \frac{\dfrac{e^{3x} - 1}{3x} \cdot 3x}{\dfrac{e^{5x} - 1}{5x} \cdot 5x}",
            r"\xrightarrow[x \to 0]{} \frac{1 \cdot 3x}{1 \cdot 5x}",
            r"\lim_{x \to 0} \frac{e^{3x} - 1}{e^{5x} - 1} = \frac{3}{5}",
        ], top=2.4)
        self.play(Write(alg[0]), run_time=1.6)

        self.cue("answer")
        self.reveal([alg[1]], alg[0])
        guide = self.guide(ax2, 0, 0.6, r"\frac{3}{5}")
        self.play(Create(guide), Write(alg[2]), run_time=1.3)
        self.box(alg[2])
        self.end_cues()
