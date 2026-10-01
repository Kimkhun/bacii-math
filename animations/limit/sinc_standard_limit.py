"""sin(u)/u -> 1, seen on the unit circle (arc vs. height), then used on
sin(5x)/(2x) by balancing the denominator."""
import math

import numpy as np
from manim import (
    LEFT, RIGHT, UP, Arc, Circle, Create, DecimalNumber, Dot, FadeIn, Line, MathTex,
    ReplacementTransform, Transform, ValueTracker, VGroup, always_redraw,
)

from common.limit_kit import LimitScene, safe
from common.style import AXIS, CURVE, CURVE_ALT, LIMIT, POINT

R = 2.4
CENTER = np.array([-3.3, -0.7, 0])


def sinc(u):
    return math.sin(u) / u if u else math.nan


class Lesson(LimitScene):
    lesson_id = "sinc_standard_limit"

    def construct(self):
        self.check("sin(x)/x", 0, 1)
        self.check("sin(5*x)/(2*x)", 0, "5/2")

        self.cue("problem")
        prob = self.problem(r"\lim_{x \to 0} \frac{\sin(5x)}{2x}")
        self.warn(r"\to \frac{0}{0}", prob, direction=RIGHT)

        # --- unit circle: arc u vs. height sin u ---------------------------
        self.cue("circle")
        # Zoom by magnifying the drawing about the point (1, 0) of the circle:
        # every piece is rebuilt each frame through ``at`` with the current
        # magnification k, so strokes stay thin however far we zoom.
        u, k = ValueTracker(1.1), ValueTracker(1.0)
        focus = CENTER + R * RIGHT

        def at(p):
            return focus + k.get_value() * (np.asarray(p) - focus)

        def tip():
            return CENTER + R * np.array([math.cos(u.get_value()), math.sin(u.get_value()), 0])

        circle = always_redraw(lambda: Circle(radius=R * k.get_value(), color=AXIS, stroke_width=2)
                               .move_to(at(CENTER)))
        axis = always_redraw(lambda: Line(at(CENTER - 1.15 * R * RIGHT), at(CENTER + 1.15 * R * RIGHT),
                                          color=AXIS, stroke_width=2))
        radius = always_redraw(lambda: Line(at(CENTER), at(tip()), color=AXIS, stroke_width=3))
        arc = always_redraw(lambda: Arc(radius=R * k.get_value(), start_angle=0, angle=u.get_value(),
                                        arc_center=at(CENTER), color=POINT, stroke_width=7))
        height = always_redraw(lambda: Line(at(tip()), at([tip()[0], CENTER[1], 0]), color=CURVE_ALT,
                                            stroke_width=7))
        dot = always_redraw(lambda: Dot(at(tip()), color=POINT, radius=0.07))
        u_label = always_redraw(lambda: MathTex("u", color=POINT).scale(0.9).next_to(
            arc.point_from_proportion(0.5), RIGHT, buff=0.15))
        s_label = always_redraw(lambda: MathTex(r"\sin u", color=CURVE_ALT).scale(0.8).next_to(
            height, LEFT, buff=0.12))
        self.play(Create(circle), Create(axis), run_time=1.2)
        self.play(Create(radius), Create(arc), FadeIn(dot), FadeIn(u_label), run_time=1.2)
        self.play(Create(height), FadeIn(s_label), run_time=1.0)

        readout = self.hud(lambda: VGroup(
            MathTex(r"u =").scale(0.8), DecimalNumber(u.get_value(), num_decimal_places=4, font_size=34, color=POINT),
            MathTex(r"\frac{\sin u}{u} =").scale(0.8),
            DecimalNumber(sinc(u.get_value()), num_decimal_places=4, font_size=34, color=LIMIT),
        ).arrange(RIGHT, buff=0.18).scale(1.2), corner=RIGHT, buff=0.5)
        self.play(FadeIn(readout), run_time=0.6)

        self.cue("shrink")
        self.play(u.animate.set_value(0.35), run_time=2.5)
        # Shrink the angle while magnifying in step, so the tiny arc and its
        # height stay big enough to compare by eye.
        self.play(u.animate.set_value(0.04), k.animate.set_value(8.0), run_time=4.5)
        self.wait(0.6)
        self.play(u.animate.set_value(0.35), k.animate.set_value(1.0), run_time=1.5)
        circle_group = VGroup(circle, axis, radius, arc, height, dot, u_label, s_label, readout)
        self.clear(circle_group)

        # --- the graph of sin(u)/u, then of sin(5x)/(2x) ---------------------
        self.cue("graph")
        ax = self.axes([-4, 4, 1], [-0.75, 3, 0.5], x_numbers=[-3, -2, -1, 1, 2, 3],
                       y_numbers=[1, 2])
        curve = self.graph(ax, safe(sinc), discontinuities=[0])
        hole = self.hole(ax, 0, 1)
        self.play(Create(ax), run_time=1.0)
        self.play(Create(curve), run_time=1.8)
        self.add(hole)
        _, riders = self.approach(ax, safe(sinc), 0, h_start=2.5, h_end=0.03, run_time=3.0)
        self.clear(riders)

        self.cue("balance")
        alg = self.column([
            r"\frac{\sin(5x)}{2x}",
            r"= \frac{5}{2} \cdot \frac{\sin(5x)}{5x}",
        ], top=2.4)
        self.derive(alg)

        self.cue("apply")
        fact = self.column([r"\frac{\sin(5x)}{5x} \xrightarrow[x \to 0]{} 1"],
                           top=alg[-1].get_bottom()[1] - 0.55)[0]
        self.play(FadeIn(fact, shift=0.2 * UP), run_time=1.0)

        self.cue("answer")
        ans = self.column([r"\lim_{x \to 0} \frac{\sin(5x)}{2x} = \frac{5}{2}"],
                          top=fact.get_bottom()[1] - 0.55)[0]
        target = self.graph(ax, safe(lambda x: math.sin(5 * x) / (2 * x)), discontinuities=[0])
        new_hole = self.hole(ax, 0, 2.5, color=CURVE)
        guide = self.guide(ax, 0, 2.5, r"\frac{5}{2}")
        self.play(Transform(curve, target), ReplacementTransform(hole, new_hole), run_time=1.8)
        self.play(Create(guide), ReplacementTransform(alg[-1].copy(), ans), run_time=1.2)
        self.box(ans)
        self.end_cues()

