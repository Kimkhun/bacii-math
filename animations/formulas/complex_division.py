"""Dividing complex numbers: flip the sign of the bottom's imaginary part to get
its conjugate, multiply top and bottom by it, watch the i vanish from the
bottom, expand the top, then split the fraction."""
from manim import LEFT, FadeIn, FadeOut, VGroup, Write

from common.formula_kit import IMAG, MINUS, REAL, FormulaScene, tex
from common.style import POINT

FRAC_X = -4.6   # centre of the fraction being transformed
WORK_X = -1.9   # left edge of the work column


def at_work(m, y):
    return m.move_to([0, y, 0]).align_to([WORK_X, 0, 0], LEFT)


class Lesson(FormulaScene):
    lesson_id = "complex_division"

    def construct(self):
        self.check("(3 + I)/(1 - I)", "1 + 2*I")

        self.cue("rule")
        self.rule(r"\frac{z_1}{z_2}", "=", r"\frac{z_1\,\overline{z_2}}{z_2\,\overline{z_2}}", "=",
                  r"\frac{z_1\,\overline{z_2}}{|z_2|^2}")

        self.cue("problem")
        frac = tex(r"\frac{", "3+i", "}{", "1-i", "}", scale=1.4).move_to([FRAC_X, 1.2, 0])
        self.play(Write(frac), run_time=1.2)
        self.flash(frac[3], color=MINUS)

        self.cue("conjugate")
        conj = at_work(tex(r"\overline{1-i}", "=", "1", "-", "i", scale=1.15), 1.75)
        self.fly([frac[3]], conj[0], run_time=1.0)
        self.play(FadeIn(conj[1]), run_time=0.3)
        self.fly([conj[0]], VGroup(conj[2], conj[3], conj[4]), run_time=0.8)
        plus = self.swap(conj[3], "+", scale=1.15)
        conj_value = VGroup(conj[2], plus, conj[4])

        self.cue("multiply")
        big = tex(r"\frac{", "(3+i)", "(1+i)", "}{", "(1-i)", "(1+i)", "}", scale=1.2).move_to([FRAC_X + 0.3, -1.05, 0])
        eq = tex("=", scale=1.2).next_to(big, LEFT, buff=0.2)
        big[2].set_color(POINT)
        big[5].set_color(POINT)
        self.play(FadeIn(eq), FadeIn(big[0]), FadeIn(big[3]), FadeIn(big[6]), run_time=0.5)
        self.fly([frac[1]], big[1], run_time=0.8)
        self.fly([frac[3]], big[4], run_time=0.8)
        self.fly(list(conj_value), big[2], run_time=0.9)
        self.fly(list(conj_value), big[5], run_time=0.9)

        self.cue("denominator")
        den = at_work(tex("(1-i)(1+i)", "=", "1^2", "-", "i^2", "=", "1+1", "=", "2", scale=0.92), 0.55)
        self.fly([big[4], big[5]], den[0], run_time=1.0)
        self.play(Write(den[1:5]), run_time=0.8)
        minus_i2 = VGroup(den[3], den[4])
        self.flash(minus_i2)
        self.play(Write(den[5:7]), run_time=0.6)
        self.play(Write(den[7:]), run_time=0.5)
        den[8].set_color(REAL)
        self.flash(den[8], color=REAL)

        self.cue("numerator")
        num = at_work(tex("(3+i)(1+i)", "=", "3", "+3i", "+i", "+i^2", "=", "2", "+4i", scale=0.92), -0.6)
        self.fly([big[1], big[2]], num[0], run_time=1.0)
        self.play(FadeIn(num[1]), run_time=0.3)
        for k in (2, 3, 4, 5):
            self.play(FadeIn(num[k], shift=0.15 * LEFT), run_time=0.45)
        self.flash(num[5])
        num[7].set_color(REAL)
        num[8].set_color(IMAG)
        self.fly([num[2], num[5]], num[7], run_time=0.9)    # 3 + i^2 = 3 - 1
        self.fly([num[3], num[4]], num[8], run_time=0.9)    # 3i + i
        self.play(FadeIn(num[6]), run_time=0.3)

        self.cue("answer")
        fin = tex("=", r"\frac{2+4i}{2}", "=", r"\frac{2}{2}", r"+\frac{4}{2}i", "=", "1", "+2i", scale=1.2)
        fin.move_to([0.6, -2.95, 0])
        fin[6].set_color(REAL)
        fin[7].set_color(IMAG)
        self.play(FadeIn(fin[0]), run_time=0.3)
        self.fly([num[7], num[8], den[8]], fin[1], run_time=1.0)
        self.play(FadeIn(fin[2]), run_time=0.3)
        # Each part of the top keeps its own copy of the 2 below.
        self.fly([fin[1]], fin[3], run_time=0.9)
        self.fly([fin[1]], fin[4], run_time=0.9)
        self.play(FadeIn(fin[5]), run_time=0.3)
        self.fly([fin[3]], fin[6], run_time=0.7)
        self.fly([fin[4]], fin[7], run_time=0.7)
        self.box(fin[6:])
        self.end_cues()
