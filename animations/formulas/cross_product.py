"""The cross product by the grid trick: write u and v as two rows, copy the x
and y columns again on the right, then slide a two-column window across. In
each window the down-right diagonal is added and the up-right one subtracted,
which is exactly each coordinate of the formula. Ends with the perpendicularity
check u . (u x v) = 0."""
from manim import LEFT, Create, DashedLine, FadeIn, FadeOut, ReplacementTransform, SurroundingRectangle, Transform, VGroup, Write

from common.formula_kit import MINUS, REAL, FormulaScene, tex
from common.style import AXIS, GRID, LIMIT, POINT

U, V = (2, -1, 3), (1, 4, -2)
RESULT = (-10, 7, 9)
COLS = [-5.0, -3.8, -2.6, -1.4, -0.2]   # x, y, z, then x and y again
HEAD_Y, U_Y, V_Y = 1.45, 0.55, -0.45
WORK_X = 1.0                            # left edge of the work column
WORK_Y = [0.95, -0.05, -1.05]

# Per coordinate: window columns, then the two products as TeX, then the value.
COMPONENTS = [
    ((1, 2), r"(-1)\cdot(-2)", r"3\cdot 4", "-10"),
    ((2, 3), r"3\cdot 1", r"2\cdot(-2)", "7"),
    ((3, 4), r"2\cdot 4", r"(-1)\cdot 1", "9"),
]


def result_line(filled: int):
    """u x v = ( . , . , . ) with the first ``filled`` coordinates written in
    and empty slots for the rest."""
    # "{-}" keeps a leading minus unary (a split piece otherwise gets binary spacing).
    slots = [str(RESULT[k]).replace("-", "{-}") if k < filled else r"\square" for k in range(3)]
    m = tex(r"\vec u\times\vec v", "=", r"\big(", slots[0], r",\;", slots[1], r",\;", slots[2], r"\big)",
            scale=1.15).move_to([0, -2.3, 0])
    for k in range(3):
        m[3 + 2 * k].set_color(LIMIT if k < filled else GRID)
    return m


class Lesson(FormulaScene):
    lesson_id = "cross_product"

    def construct(self):
        self.check("Matrix([2, -1, 3]).cross(Matrix([1, 4, -2]))", "Matrix([-10, 7, 9])")
        self.check("Matrix([2, -1, 3]).dot(Matrix([-10, 7, 9]))", "0")

        self.cue("rule")
        self.rule(r"\vec u\times\vec v", "=", r"\big(", "y_1z_2-z_1y_2", r",\;", "z_1x_2-x_1z_2",
                  r",\;", "x_1y_2-y_1x_2", r"\big)")

        self.cue("setup")
        u = tex(r"\vec u", "=", "(", "2", ",", "-1", ",", "3", ")").move_to([-3.4, 2.25, 0])
        v = tex(r"\vec v", "=", "(", "1", ",", "4", ",", "-2", ")").move_to([2.4, 2.25, 0])
        self.play(Write(u), Write(v), run_time=1.4)
        heads = [tex(h, color=AXIS).move_to([x, HEAD_Y, 0]) for h, x in zip("xyz", COLS)]
        labels = VGroup(tex(r"\vec u").move_to([COLS[0] - 1.3, U_Y, 0]),
                        tex(r"\vec v").move_to([COLS[0] - 1.3, V_Y, 0]))
        self.play(FadeIn(VGroup(*heads)), FadeIn(labels), run_time=0.6)
        cells = {}  # (row, col) -> mobject
        for row, (vec, src, y) in enumerate(((U, u, U_Y), (V, v, V_Y))):
            for col in range(3):
                cells[row, col] = tex(str(vec[col])).move_to([COLS[col], y, 0])
                self.fly([src[3 + 2 * col]], cells[row, col], run_time=0.6)

        self.cue("repeat")
        sep = DashedLine([(COLS[2] + COLS[3]) / 2, HEAD_Y + 0.4, 0], [(COLS[2] + COLS[3]) / 2, V_Y - 0.4, 0],
                         color=GRID, stroke_width=2)
        self.play(Create(sep), run_time=0.5)
        for col in (0, 1):
            heads.append(tex("xyz"[col], color=AXIS).move_to([COLS[col + 3], HEAD_Y, 0]))
            for row, y in ((0, U_Y), (1, V_Y)):
                cells[row, col + 3] = tex(str((U, V)[row][col])).move_to([COLS[col + 3], y, 0])
            self.fly([heads[col], cells[0, col], cells[1, col]],
                     VGroup(heads[-1], cells[0, col + 3], cells[1, col + 3]), run_time=1.1)

        result = result_line(0)

        window = arrows = None
        for k, (cue, (lo, hi), plus, minus, value) in enumerate(
                zip(("x_comp", "y_comp", "z_comp"), *zip(*COMPONENTS))):
            self.cue(cue)
            block = VGroup(cells[0, lo], cells[0, hi], cells[1, lo], cells[1, hi], heads[lo], heads[hi])
            if window is None:
                window = SurroundingRectangle(block, color=POINT, buff=0.2, corner_radius=0.1)
                self.play(Create(window), FadeIn(result), run_time=0.8)
            else:
                self.play(FadeOut(arrows), window.animate.move_to(block), run_time=0.9)
            self.flash(result[3 + 2 * k])
            down = self.straight(cells[0, lo], cells[1, hi], color=REAL)
            up = self.straight(cells[0, hi], cells[1, lo], color=MINUS)
            arrows = VGroup(down, up)
            work = tex(plus, "-", minus, "=", value, scale=0.95)
            work.move_to([0, WORK_Y[k], 0]).align_to([WORK_X, 0, 0], LEFT)
            work[0].set_color(REAL)
            work[2].set_color(MINUS)
            self.fly([cells[0, lo], cells[1, hi]], work[0], run_time=0.9)
            self.play(FadeIn(work[1]), run_time=0.3)
            self.fly([cells[0, hi], cells[1, lo]], work[2], run_time=0.9)
            self.play(Write(work[3:]), run_time=0.6)
            # The value flies into its slot while the rest of the line makes room.
            slot = 3 + 2 * k
            filled = result_line(k + 1)
            self.play(*[Transform(result[i], filled[i]) for i in range(len(filled)) if i != slot],
                      FadeOut(result[slot]), ReplacementTransform(work[4].copy(), filled[slot]), run_time=0.9)
            result.submobjects[slot] = filled[slot]

        self.cue("answer")
        self.play(FadeOut(arrows), FadeOut(window), run_time=0.5)
        self.box(result[2:])

        self.cue("check")
        check = tex(r"\vec u\cdot(\vec u\times\vec v)", "=", r"2(-10)", r"+(-1)(7)", r"+3(9)", "=", "0", scale=0.95)
        check.move_to([0, -3.4, 0])
        self.play(Write(check[0:2]), run_time=0.8)
        for i, k in enumerate((3, 5, 7)):
            self.fly([u[3 + 2 * i], result[k]], check[2 + i], run_time=0.8)
        self.play(Write(check[5:]), run_time=0.6)
        self.box(check[6])
        self.end_cues()
