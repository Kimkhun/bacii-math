"""Conjugate at infinity: infinity minus infinity becomes 4x / (sqrt + x)."""
import math

from common.limit_kit import LimitScene


class Lesson(LimitScene):
    lesson_id = "conjugate_infinity"

    def construct(self):
        self.check("sqrt(x**2 + 4*x) - x", "oo", 2)
        self.infinity_story(
            problem=r"\lim_{x \to +\infty} \left(\sqrt{x^2 + 4x} - x\right)", form=r"\infty - \infty",
            f=lambda x: math.sqrt(x * x + 4 * x) - x, L=2, L_label="2",
            x_range=[0, 40, 10], y_range=[0, 3, 1], x_numbers=[10, 20, 30, 40], y_numbers=[1],
            x_start=0.5, plot_from=0.01,
            algebra=[
                ("conjugate", [r"\sqrt{x^2 + 4x} - x = \frac{(x^2 + 4x) - x^2}{\sqrt{x^2 + 4x} + x}",
                               r"= \frac{4x}{\sqrt{x^2 + 4x} + x}"]),
                ("divide", [r"= \frac{4}{\sqrt{1 + \frac{4}{x}} + 1}"]),
            ],
            answer=r"\lim_{x \to +\infty} \left(\sqrt{x^2 + 4x} - x\right) = \frac{4}{1 + 1} = 2",
        )
