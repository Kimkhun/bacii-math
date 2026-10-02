"""Angle addition: the numerator sin x - sqrt(3) cos x is one shifted sine wave
2 sin(x - pi/3), turning the quotient into 2 sin(t)/t."""
import math

from manim import Create, Dot, FadeIn, FadeOut, ReplacementTransform, Transform, VGroup, Write

from common.limit_kit import LimitScene, red, safe
from common.style import CURVE_ALT, POINT

A = math.pi / 3


def numerator(x):
    return math.sin(x) - math.sqrt(3) * math.cos(x)


def quotient(x):
    return numerator(x) / (x - A)


class Lesson(LimitScene):
    lesson_id = "angle_addition_0_0"

    def construct(self):
        self.check("(sin(x) - sqrt(3)*cos(x))/(x - pi/3)", "pi/3", 2)

        self.cue("problem")
        self.problem(r"\lim_{x \to \frac{\pi}{3}} \frac{\sin x - \sqrt{3}\cos x}{x - \frac{\pi}{3}}")

        self.cue("substitute")
        sub = self.column([
            r"\frac{\sin\frac{\pi}{3} - \sqrt{3}\cos\frac{\pi}{3}}{\frac{\pi}{3} - \frac{\pi}{3}}",
            r"= \frac{\frac{\sqrt{3}}{2} - \frac{\sqrt{3}}{2}}{0} = \frac{0}{0}",
        ], top=2.5)
        self.derive(sub)
        red(sub[-1])

        self.cue("combine")
        ax = self.axes([-1.5, 4.5, 1], [-2.5, 2.5, 1], x_numbers=[-1, 1, 2, 3, 4], y_numbers=[-2, 2])
        label = self.xlabel(ax, A, r"\frac{\pi}{3}")
        wave = self.graph(ax, numerator)
        self.play(Create(ax), run_time=1.0)
        self.play(Create(wave), run_time=1.6)
        self.clear(*sub)
        alg = self.column([
            r"\sin x - \sqrt{3}\cos x",
            r"= 2\left(\tfrac{1}{2}\sin x - \tfrac{\sqrt{3}}{2}\cos x\right)",
            r"= 2\sin\left(x - \frac{\pi}{3}\right)",
        ], top=2.5)
        self.derive(alg)
        shifted = self.graph(ax, lambda x: 2 * math.sin(x - A), color=CURVE_ALT, width=6)
        zero = Dot(ax.c2p(A, 0), color=POINT, radius=0.08)
        self.play(Create(shifted), run_time=1.4)
        self.play(FadeIn(zero, scale=2), FadeIn(label), run_time=0.6)

        self.cue("rewrite")
        rest = self.column([
            r"\frac{\sin x - \sqrt{3}\cos x}{x - \frac{\pi}{3}} = 2 \cdot \frac{\sin t}{t}",
            r"t = x - \frac{\pi}{3} \to 0",
            r"\lim_{x \to \frac{\pi}{3}} \frac{\sin x - \sqrt{3}\cos x}{x - \frac{\pi}{3}} = 2 \cdot 1 = 2",
        ], top=2.5)
        self.play(FadeOut(VGroup(*alg[:2])), ReplacementTransform(alg[2], rest[0]), run_time=1.3)
        self.play(Write(rest[1]), run_time=1.0)

        self.cue("graph")
        quot = self.graph(ax, safe(quotient), discontinuities=[A])
        hole = self.hole(ax, A, 2)
        self.play(FadeOut(shifted), FadeOut(zero), Transform(wave, quot), run_time=1.8)
        self.add(hole)
        _, riders = self.approach(ax, safe(quotient), A, h_start=2.2, h_end=0.02)

        self.cue("answer")
        self.clear(riders)
        guide = self.guide(ax, A, 2, "2")
        self.play(Create(guide), Write(rest[2]), run_time=1.3)
        self.box(rest[2])
        self.end_cues()
