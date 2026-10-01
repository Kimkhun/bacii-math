"""Rational function at infinity: only the leading terms survive."""
from common.limit_kit import LimitScene


class Lesson(LimitScene):
    lesson_id = "rational_function_infinity"

    def construct(self):
        self.check("(3*x**2 + 5*x)/(2*x**2 - 7)", "oo", "3/2")
        self.infinity_story(
            problem=r"\lim_{x \to +\infty} \frac{3x^2 + 5x}{2x^2 - 7}", form=r"\frac{\infty}{\infty}",
            f=lambda x: (3 * x * x + 5 * x) / (2 * x * x - 7), L=1.5, L_label=r"\frac{3}{2}",
            x_range=[0, 40, 10], y_range=[0, 4.5, 1], x_numbers=[10, 20, 30, 40], y_numbers=[3],
            x_start=3.0, plot_from=3.0,
            algebra=[
                ("dominant", [r"3x^2 \gg 5x, \qquad 2x^2 \gg 7"]),
                ("divide", [r"\frac{3x^2 + 5x}{2x^2 - 7} = \frac{3 + \frac{5}{x}}{2 - \frac{7}{x^2}}"]),
            ],
            answer=r"\lim_{x \to +\infty} \frac{3x^2 + 5x}{2x^2 - 7} = \frac{3}{2}",
        )
