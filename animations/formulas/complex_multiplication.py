"""Multiplying complex numbers: expand like ordinary brackets (four arrows,
four products), turn i^2 into -1, collect real and imaginary parts — then show
that the formula (ac - bd) + (ad + bc)i is just that work done in advance."""
from manim import DOWN, LEFT, FadeIn, FadeOut, VGroup, Write

from common.formula_kit import IMAG, REAL, FormulaScene, tex
from common.style import POINT

LEFT_X = -3.0   # centre of the worked-example column
RIGHT_X = 0.5   # left edge of the "this is the formula" column


class Lesson(FormulaScene):
    lesson_id = "complex_multiplication"

    def construct(self):
        self.check("(2 + 3*I)*(4 - I)", "11 + 10*I")

        self.cue("rule")
        rule = self.rule("(a+bi)(c+di)", "=", "(", "ac-bd", ")", "+", "(", "ad+bc", ")", "i")

        self.cue("example")
        ex = tex("(", "2", "+3i", ")", "(", "4", "-i", ")", scale=1.35).move_to([LEFT_X, 1.5, 0])
        self.play(Write(ex), run_time=1.4)
        a, b, c, d = ex[1], ex[2], ex[5], ex[6]

        self.cue("distribute")
        prods = tex("8", "-2i", "+12i", "-3i^2", scale=1.2).move_to([LEFT_X, -0.25, 0])
        arrows = []
        # Outer pairs arc above the brackets, inner pairs below, so no two cross.
        for (p, q, above), target in zip([(a, c, True), (a, d, True), (b, c, False), (b, d, False)], prods):
            arrows.append(self.point(p, q, above=above, bend=1.1 if q is d else 0.9))
            self.fly([p, q], target, run_time=0.9)
        self.play(*[FadeOut(arr) for arr in arrows], run_time=0.5)

        self.cue("i_squared")
        note = tex("i^2", "=", "-1", scale=0.9, color=POINT).next_to(prods[3], DOWN, buff=0.35)
        self.play(FadeIn(note), run_time=0.6)
        step = self.swap(prods[3], r"{}-3\cdot(-1)", scale=1.2)
        plus3 = self.swap(step, "{}+3", scale=1.2)
        self.play(FadeOut(note), run_time=0.4)

        self.cue("group")
        for m, color in ((prods[0], REAL), (plus3, REAL), (prods[1], IMAG), (prods[2], IMAG)):
            m.set_color(color)
        grouped = tex("=", "(", "8", "+3", ")", "+", "(", "-2", "+12", ")", "i", scale=1.2)
        grouped.move_to([LEFT_X, -1.45, 0])
        grouped[2:4].set_color(REAL)
        grouped[7:11].set_color(IMAG)
        self.play(FadeIn(grouped[0:2]), FadeIn(grouped[4:7]), FadeIn(grouped[9:11]), run_time=0.5)
        self.fly([prods[0]], grouped[2], run_time=0.8)
        self.fly([plus3], grouped[3], run_time=0.8)
        self.fly([prods[1]], grouped[7], run_time=0.8)
        self.fly([prods[2]], grouped[8], run_time=0.8)

        self.cue("answer")
        ans = tex("=", "11", "+", "10", "i", scale=1.35).move_to([LEFT_X, -2.75, 0])
        ans[1].set_color(REAL)
        ans[3:5].set_color(IMAG)
        self.play(FadeIn(ans[0]), FadeIn(ans[2]), run_time=0.4)
        self.fly([grouped[1:5]], ans[1])
        self.fly([grouped[6:11]], VGroup(ans[3], ans[4]))
        self.box(ans[1:])

        self.cue("shortcut")
        rule[3].set_color(REAL)
        rule[7].set_color(IMAG)
        self.flash(rule[3], rule[7])
        real = tex("ac-bd", "=", r"2\cdot 4", r"-3\cdot(-1)", "=", "11", scale=0.92)
        imag = tex("ad+bc", "=", r"2\cdot(-1)", r"+3\cdot 4", "=", "10", scale=0.92)
        real.move_to([0, 0.75, 0]).align_to([RIGHT_X, 0, 0], LEFT)
        imag.move_to([0, -0.55, 0]).align_to([RIGHT_X, 0, 0], LEFT)
        for line, src, color in ((real, rule[3], REAL), (imag, rule[7], IMAG)):
            line[0].set_color(color)
            line[5].set_color(color)
            self.fly([src], line[0], run_time=1.0)
            self.play(FadeIn(line[1]), run_time=0.3)
        self.fly([a, c], real[2], run_time=0.9)
        self.fly([b, d], real[3], run_time=0.9)
        self.fly([a, d], imag[2], run_time=0.9)
        self.fly([b, c], imag[3], run_time=0.9)
        self.play(Write(real[4:]), Write(imag[4:]), run_time=0.8)
        self.flash(real[5], ans[1], color=REAL)
        self.flash(imag[5], ans[3], color=IMAG)
        self.end_cues()
