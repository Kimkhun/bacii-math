"""Building blocks shared by the limit lesson scenes.

Every limit video follows the same storyboard — state the problem, try the
naive substitution, look at the graph (points sliding in from both sides, a
zoom into the hole), run the lesson's algebra trick, box the answer — so the
moves live here and each ``animations/limit/<lesson>.py`` is mostly the
choice of function, window and algebra lines.

The answer a scene boxes is checked against SymPy at render time
(``LimitScene.check``), so a video can never show a value the grader would
reject.
"""
import math

import numpy as np
import sympy as sp
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UL,
    UP,
    Axes,
    Circle,
    Create,
    DashedLine,
    DecimalNumber,
    Dot,
    FadeIn,
    FadeOut,
    MathTex,
    SurroundingRectangle,
    TransformMatchingTex,
    ValueTracker,
    VGroup,
    Write,
    always_redraw,
    config,
    linear,
    smooth,
)

from .captioned import CaptionedScene
from .style import AXIS, CURVE, CURVE_ALT, LIMIT, POINT, WARN

#: Left half of the frame holds the graph, the right half the algebra.
GRAPH_CENTER = LEFT * 3.4 + DOWN * 0.45
ALGEBRA_LEFT = 0.4


class LimitScene(CaptionedScene):
    topic = "limit"

    # ---- correctness ---------------------------------------------------
    @staticmethod
    def check(expr: str, point, expected, side: str = "+-") -> None:
        """Assert SymPy agrees with the value this scene is about to show.
        ``point`` may be ``"oo"``; ``side`` is ``"+-"`` (two-sided), ``"+"`` or
        ``"-"``; ``expected`` is anything SymPy can parse."""
        x = sp.Symbol("x", real=True)
        f = sp.sympify(expr, locals={"x": x})
        if point == "oo":
            got = sp.limit(f, x, sp.oo)
        else:
            got = sp.limit(f, x, sp.sympify(point), dir=side)
        want = sp.sympify(expected)
        if sp.simplify(got - want) != 0:
            raise AssertionError(f"lim {expr} at {point}: SymPy says {got}, scene shows {want}")

    # ---- text ------------------------------------------------------------
    def problem(self, tex: str, scale: float = 1.1) -> MathTex:
        m = MathTex(tex).scale(scale).to_corner(UL, buff=0.45)
        self.play(Write(m), run_time=1.6)
        return m

    def column(self, lines: list[str], top, scale: float = 1.0, gap: float = 0.5,
               bottom: float = -3.75, max_width: float = 6.2) -> list[MathTex]:
        """MathTex lines for the algebra column, stacked under ``top`` and
        left-aligned at ``ALGEBRA_LEFT`` (not yet added to the scene). Lines
        too wide for the right half are shrunk, and the whole column shrinks
        if it would run off the bottom of the frame."""
        out = []
        for tex in lines:
            m = MathTex(tex).scale(scale)
            if m.width > max_width:
                m.scale_to_fit_width(max_width)
            out.append(m)
        total = sum(m.height for m in out) + gap * (len(out) - 1)
        shrink = min(1.0, (top - bottom) / total)
        y = top
        for m in out:
            m.scale(shrink)
            m.move_to([ALGEBRA_LEFT + m.width / 2, y - m.height / 2, 0])
            y -= m.height + gap * shrink
        return out

    def reveal(self, mobs: list[MathTex], prev: MathTex | None = None, run_time: float = 1.3):
        """Like ``derive`` but continuing a column: the first line grows out of
        ``prev`` (or is written, when there is none)."""
        for m in mobs:
            if prev is None:
                self.play(Write(m), run_time=run_time)
            else:
                self.play(TransformMatchingTex(prev.copy(), m), run_time=run_time)
                self.wait(0.4)
            prev = m

    def derive(self, mobs: list[MathTex], run_time: float = 1.3):
        """Reveal an algebra column line by line, each new line growing out of
        the previous one (matching pieces glide into place)."""
        self.play(Write(mobs[0]), run_time=run_time)
        for prev, nxt in zip(mobs, mobs[1:]):
            self.play(TransformMatchingTex(prev.copy(), nxt), run_time=run_time)
            self.wait(0.4)

    def box(self, mob, color=LIMIT):
        rect = SurroundingRectangle(mob, color=color, buff=0.15, corner_radius=0.08)
        self.play(Create(rect), run_time=0.8)
        return rect

    # ---- graph -----------------------------------------------------------
    def axes(self, x_range, y_range, width=6.2, height=4.9, x_numbers=None, y_numbers=None,
             center=GRAPH_CENTER) -> Axes:
        ax = Axes(
            x_range=x_range, y_range=y_range, x_length=width, y_length=height, tips=False,
            axis_config={"color": AXIS, "stroke_width": 2, "include_ticks": True,
                         "tick_size": 0.06},
        ).move_to(center)
        if x_numbers:
            ax.x_axis.add_numbers(x_numbers, font_size=30, num_decimal_places=0)
        if y_numbers:
            ax.y_axis.add_numbers(y_numbers, font_size=30, num_decimal_places=0)
        return ax

    def graph(self, ax: Axes, f, x_range=None, color=CURVE, discontinuities=None, width=4):
        lo, hi = (x_range or ax.x_range[:2])[:2]
        return ax.plot(f, x_range=[lo, hi, (hi - lo) / 400], color=color, stroke_width=width,
                       discontinuities=discontinuities, dt=1e-3, use_smoothing=False)

    def hole(self, ax: Axes, a: float, L: float, color=CURVE, radius=0.08):
        """An open circle at (a, L); keeps its on-screen size while zooming."""
        return always_redraw(lambda: Circle(radius=self.px(radius), color=color, stroke_width=4)
                             .set_fill(self.camera.background_color, opacity=1).move_to(ax.c2p(a, L)))

    def guide(self, ax: Axes, a: float, L: float, label: str | None = None, color=LIMIT):
        """Dashed lines from the point (a, L) down to the x-axis and across to the y-axis."""
        g = VGroup(
            DashedLine(ax.c2p(a, 0), ax.c2p(a, L), color=color, stroke_width=2.5),
            DashedLine(ax.c2p(ax.x_range[0], L), ax.c2p(a, L), color=color, stroke_width=2.5),
        )
        if label:
            g.add(MathTex(label, color=color).scale(0.85).next_to(ax.c2p(ax.x_range[0], L), LEFT, 0.12))
        return g

    def asymptote(self, ax: Axes, L: float, label: str | None = None, color=LIMIT):
        """Dashed horizontal line y = L across the whole window."""
        g = VGroup(DashedLine(ax.c2p(ax.x_range[0], L), ax.c2p(ax.x_range[1], L), color=color,
                              stroke_width=2.5))
        if label:
            g.add(MathTex(label, color=color).scale(0.85).next_to(ax.c2p(ax.x_range[0], L), LEFT, 0.12))
        return g

    def xlabel(self, ax: Axes, x: float, tex: str):
        """A tick label at ``x`` written as LaTeX (for values like pi/2)."""
        return MathTex(tex).scale(0.65).next_to(ax.c2p(x, 0), DOWN, buff=0.15)

    def approach(self, ax: Axes, f, a: float, h_start: float, h_end: float = 0.02,
                 run_time: float = 4.0, decimals: int = 3, color=POINT, sides=(-1, 1),
                 animate: bool = True):
        """Two points ride the curve toward ``x = a`` from the left and right,
        each with a live readout of f(x). Returns (tracker, group) so a caller
        can keep pushing ``h`` (e.g. while zoomed in) and fade the group later."""
        h = ValueTracker(h_start)
        group = VGroup()
        for s in sides:
            def pos(s=s):
                x = a + s * h.get_value()
                return ax.c2p(x, f(x))
            side = (UP + LEFT * 0.6) if s < 0 else (DOWN + RIGHT * 0.6)
            dot = always_redraw(lambda pos=pos: Dot(pos(), color=color, radius=self.px(0.07)))
            val = always_redraw(lambda pos=pos, s=s, side=side: DecimalNumber(
                f(a + s * h.get_value()), num_decimal_places=decimals, font_size=34, color=color,
            ).scale(self.px(1)).next_to(pos(), side, buff=self.px(0.12)))
            group.add(dot, val)
        self.play(FadeIn(group), run_time=0.6)
        if animate:
            self.play(h.animate.set_value(h_end), run_time=run_time, rate_func=smooth)
        return h, group

    def run_to_infinity(self, ax: Axes, f, x_start: float, x_end: float, run_time: float = 4.5,
                        decimals: int = 3, color=POINT):
        """One point rides the curve off to the right with x and f(x) readouts
        pinned under the graph."""
        t = ValueTracker(x_start)
        dot = always_redraw(lambda: Dot(ax.c2p(t.get_value(), f(t.get_value())), color=color, radius=0.07))
        readout = always_redraw(lambda: VGroup(
            MathTex("x =").scale(0.7),
            DecimalNumber(t.get_value(), num_decimal_places=0, font_size=30),
            MathTex(r"\quad f(x) =").scale(0.7),
            DecimalNumber(f(t.get_value()), num_decimal_places=decimals, font_size=30, color=color),
        ).arrange(RIGHT, buff=0.15).next_to(ax, DOWN, buff=0.3))
        group = VGroup(dot, readout)
        self.play(FadeIn(group), run_time=0.6)
        self.play(t.animate.set_value(x_end), run_time=run_time, rate_func=linear)
        return t, group

    # ---- camera ----------------------------------------------------------
    # Zooming scales the *content* about a point rather than moving the camera:
    # Manim keeps stroke widths fixed when a mobject is scaled, so curves stay
    # crisp at any magnification, and dots / holes / readouts — redrawn every
    # frame from ``ax.c2p`` — keep their on-screen size automatically.
    def zoom_to(self, content, point, factor: float = 5.0, hide=(), run_time: float = 2.0):
        """Magnify ``content`` (axes + curves) ``factor`` times about ``point``,
        fading ``hide`` (text that would collide with the enlarged graph)."""
        self._zoom = (content, point, factor, hide)
        anims = [content.animate.scale(factor, about_point=point)]
        anims += [m.animate.set_opacity(0) for m in hide]
        self.play(*anims, run_time=run_time)

    def zoom_back(self, run_time: float = 1.6):
        content, point, factor, hide = self._zoom
        anims = [content.animate.scale(1 / factor, about_point=point)]
        anims += [m.animate.set_opacity(1) for m in hide]
        self.play(*anims, run_time=run_time)

    def px(self, size: float) -> float:
        """Kept for scenes that size things relative to the camera frame."""
        return size * self.camera.frame.width / config.frame_width

    def hud(self, build, corner=UP + RIGHT, buff: float = 0.4):
        """A mobject pinned to a corner of the frame, rebuilt every frame."""
        def place():
            m = build()
            frame = self.camera.frame
            half = np.array([m.width / 2, m.height / 2, 0])
            return m.move_to(frame.get_corner(corner) - corner * (half + buff))
        return always_redraw(place)

    # ---- whole storyboards ---------------------------------------------------
    def hole_story(self, *, problem: str, substitution: list[str], f, a: float, L: float,
                   x_range, y_range, algebra: list[tuple[str, list[str]]], answer: str,
                   L_label: str, x_numbers=None, y_numbers=None, x_labels=(),
                   h_start: float = 1.0, h_end: float = 0.02, decimals: int = 3,
                   plot_range=None, simplified=None):
        """The 0/0 storyboard shared by most finite-point lessons. Cues used, in
        order: ``problem``, ``substitute``, ``graph``, ``approach``, one cue per
        ``algebra`` group, ``answer``."""
        self.cue("problem")
        prob = self.problem(problem)

        self.cue("substitute")
        sub = self.column(substitution, top=2.5)
        self.derive(sub)
        red(sub[-1])

        self.cue("graph")
        ax = self.axes(x_range, y_range, x_numbers=x_numbers, y_numbers=y_numbers)
        labels = VGroup(*[self.xlabel(ax, x, tex) for x, tex in x_labels])
        curve = self.graph(ax, safe(f), x_range=plot_range, discontinuities=[a])
        hole = self.hole(ax, a, L)
        self.play(Create(ax), FadeIn(labels), run_time=1.0)
        self.play(Create(curve), run_time=1.8)
        self.add(hole)

        self.cue("approach")
        _, riders = self.approach(ax, safe(f), a, h_start=h_start, h_end=h_end, decimals=decimals)

        lines = [ln for _, group in algebra for ln in group] + [answer]
        alg = self.column(lines, top=2.5)
        i, prev = 0, None
        for k, (cue, group) in enumerate(algebra):
            self.cue(cue)
            if k == 0:
                self.clear(riders, *sub)
            self.reveal(alg[i:i + len(group)], prev)
            prev, i = alg[i + len(group) - 1], i + len(group)
            if simplified is not None and k == len(algebra) - 1:
                fill = self.graph(ax, simplified, x_range=plot_range, color=CURVE_ALT, width=5)
                self.play(Create(fill), FadeOut(hole), run_time=1.4)

        self.cue("answer")
        guide = self.guide(ax, a, L, L_label)
        self.play(Create(guide), Write(alg[-1]), run_time=1.3)
        self.box(alg[-1])
        self.end_cues()
        return prob, ax

    def infinity_story(self, *, problem: str, form: str, f, L: float, x_range, y_range,
                       algebra: list[tuple[str, list[str]]], answer: str, L_label: str,
                       x_numbers=None, y_numbers=None, x_start: float = 0.5, plot_from=None,
                       decimals: int = 3):
        """The x -> +infinity storyboard. Cues: ``problem``, ``form``, ``graph``,
        one per ``algebra`` group, ``answer``."""
        self.cue("problem")
        prob = self.problem(problem)

        self.cue("form")
        self.warn(r"\to " + form, prob, direction=RIGHT)

        self.cue("graph")
        ax = self.axes(x_range, y_range, x_numbers=x_numbers, y_numbers=y_numbers)
        lo = plot_from if plot_from is not None else x_start
        curve = self.graph(ax, safe(f), x_range=[lo, x_range[1]])
        self.play(Create(ax), run_time=1.0)
        self.play(Create(curve), run_time=1.8)
        _, rider = self.run_to_infinity(ax, safe(f), x_start, x_range[1], decimals=decimals)
        asym = self.asymptote(ax, L, L_label)
        self.play(Create(asym), run_time=1.0)

        lines = [ln for _, group in algebra for ln in group] + [answer]
        alg = self.column(lines, top=2.3)
        i, prev = 0, None
        for cue, group in algebra:
            self.cue(cue)
            self.reveal(alg[i:i + len(group)], prev)
            prev, i = alg[i + len(group) - 1], i + len(group)

        self.cue("answer")
        self.play(Write(alg[-1]), run_time=1.3)
        self.box(alg[-1])
        self.end_cues()
        return prob, ax, rider

    # ---- small helpers -----------------------------------------------------
    def warn(self, tex: str, next_to, direction=DOWN, scale: float = 0.9) -> MathTex:
        m = MathTex(tex, color=WARN).scale(scale).next_to(next_to, direction, buff=0.35)
        self.play(FadeIn(m, shift=0.2 * UP), run_time=0.7)
        return m

    def clear(self, *mobs, run_time: float = 0.6):
        self.play(*[FadeOut(m) for m in mobs], run_time=run_time)


def safe(f):
    """Wrap a float function so the plotter / readouts never see a domain error
    exactly at the excluded point (returns NaN there instead of raising)."""
    def g(x):
        try:
            return f(x)
        except (ZeroDivisionError, ValueError, OverflowError):
            return math.nan
    return g


def red(m: MathTex) -> MathTex:
    return m.set_color(WARN)
