"""Building blocks for formula tutorials: a worked example of one formula from
the formula sheet, played out with arrows and moving numbers.

Every tutorial follows the same shape: the general rule sits in a banner at the
top, a concrete example is written under it, and each step is shown by
*pointing* (an arrow from the pieces being combined), *moving* (copies of those
pieces fly to where their result goes and turn into it) and *highlighting* the
piece that changes. The final result is boxed and checked against SymPy at
render time (``FormulaScene.check``), so a tutorial can never show a value the
grader would reject.

Scenes live in ``animations/formulas/<formula_id>.py``; captions in
``backend/engine/data/formula_animations.json`` (see ``captioned.py``).
"""
import sympy as sp
from manim import (
    DOWN,
    LEFT,
    UP,
    Arrow,
    Create,
    CurvedArrow,
    FadeIn,
    FadeOut,
    Indicate,
    MathTex,
    ReplacementTransform,
    RoundedRectangle,
    SurroundingRectangle,
    VGroup,
    Write,
)

from .captioned import FORMULAS, CaptionedScene
from .style import GRID, LIMIT, POINT

#: Colours with a fixed meaning across every tutorial.
REAL = "#58c4dd"   # real parts / the first kind of term being collected (3b1b blue)
IMAG = "#f0ac5f"   # imaginary parts / the second kind (orange)
MINUS = "#fc6255"  # the subtracted product, a sign that flips
RULE_Y = 3.15      # vertical centre of the rule banner


class FormulaScene(CaptionedScene):
    topic = FORMULAS

    # ---- correctness ---------------------------------------------------
    @staticmethod
    def check(computed: str, shown: str) -> None:
        """Assert SymPy evaluates ``computed`` (the example, as SymPy source:
        ``I`` is the imaginary unit, ``Matrix`` is available) to ``shown``,
        the result the scene boxes."""
        env = {"I": sp.I, "Matrix": sp.Matrix}
        got = sp.sympify(computed, locals=env)
        want = sp.sympify(shown, locals=env)
        diff = got - want
        zero = diff.is_zero_matrix if isinstance(diff, sp.MatrixBase) else sp.simplify(sp.expand(diff)) == 0
        if not zero:
            raise AssertionError(f"{computed}: SymPy says {got}, scene shows {want}")

    # ---- the rule ---------------------------------------------------------
    def rule(self, *pieces: str, max_width: float = 12.4) -> MathTex:
        """The general formula in a quiet banner at the top of the frame. It
        stays up for the whole tutorial so later steps can point back at it."""
        m = MathTex(*pieces)
        if m.width > max_width:
            m.scale_to_fit_width(max_width)
        m.move_to([0, RULE_Y, 0])
        panel = RoundedRectangle(width=m.width + 0.6, height=m.height + 0.4, corner_radius=0.15,
                                 stroke_color=GRID, stroke_width=2).move_to(m)
        panel.set_fill("#1a1f29", opacity=1)
        self.play(FadeIn(panel), Write(m), run_time=1.8)
        self.rule_panel = panel
        return m

    # ---- pointing ----------------------------------------------------------
    def point(self, src, dst, color=POINT, above: bool = True, bend: float = 0.9, width: float = 4,
              run_time: float = 0.7) -> CurvedArrow:
        """A curved arrow from ``src`` to ``dst`` bowing above (or below) the
        line they sit on: "this one meets that one"."""
        side = UP if above else DOWN
        start = src.get_edge_center(side) + 0.08 * side
        end = dst.get_edge_center(side) + 0.08 * side
        # Manim arcs bend counter-clockwise for a positive angle; going left to
        # right that is *below* the chord, so flip the sign to bow upwards.
        sign = 1 if (end[0] >= start[0]) != above else -1
        arrow = CurvedArrow(start, end, angle=sign * bend, color=color, stroke_width=width,
                            tip_length=0.18)
        self.play(Create(arrow), run_time=run_time)
        return arrow

    def straight(self, src, dst, color=POINT, buff: float = 0.12, run_time: float = 0.6) -> Arrow:
        """A straight arrow between two mobjects (e.g. a diagonal across a grid)."""
        arrow = Arrow(src.get_center(), dst.get_center(), buff=buff + max(src.width, src.height) / 2,
                      color=color, stroke_width=5, max_tip_length_to_length_ratio=0.18)
        self.play(Create(arrow), run_time=run_time)
        return arrow

    # ---- moving ---------------------------------------------------------------
    def fly(self, sources, target, run_time: float = 1.1, keep: bool = True):
        """Copies of ``sources`` travel to ``target``'s place and morph into it.
        The originals stay where they are (``keep``) so the student can see
        where the result came from."""
        sources = sources if isinstance(sources, (list, tuple)) else [sources]
        copies = VGroup(*[s.copy() for s in sources])
        if not keep:
            self.remove(*sources)
        self.play(ReplacementTransform(copies, target), run_time=run_time)
        return target

    def swap(self, old, new_tex: str, scale: float = 1.0, color=POINT, run_time: float = 0.9) -> MathTex:
        """Replace one piece in place by a new one (e.g. ``-3i^2`` -> ``+3``)
        with a flash. The new piece starts where the old one started, so a
        line's last term can grow to the right without covering its
        neighbours. ``scale`` is the scale of the line ``old`` sits in."""
        new = MathTex(new_tex, color=color).scale(scale).move_to(old).align_to(old, LEFT)
        self.play(Indicate(old, color=color, scale_factor=1.25), run_time=0.6)
        self.play(ReplacementTransform(old, new), run_time=run_time)
        return new

    def flash(self, *mobs, color=POINT, run_time: float = 0.8):
        self.play(*[Indicate(m, color=color, scale_factor=1.2) for m in mobs], run_time=run_time)

    # ---- result -----------------------------------------------------------------
    def box(self, mob, color=LIMIT):
        rect = SurroundingRectangle(mob, color=color, buff=0.15, corner_radius=0.08)
        self.play(Create(rect), run_time=0.8)
        return rect

    def clear(self, *mobs, run_time: float = 0.6):
        self.play(*[FadeOut(m) for m in mobs], run_time=run_time)


def tex(*pieces: str, scale: float = 1.0, color=None) -> MathTex:
    """A split MathTex (one submobject per piece) not yet added to the scene."""
    m = MathTex(*pieces).scale(scale)
    if color is not None:
        m.set_color(color)
    return m
