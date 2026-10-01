"""1^infinity: rewrite as [(1 + u)^(1/u)]^3 with u = 3/x, which tends to e^3."""
import math

from common.limit_kit import LimitScene


class Lesson(LimitScene):
    lesson_id = "indeterminate_one_infinity"

    def construct(self):
        self.check("(1 + 3/x)**x", "oo", "exp(3)")
        self.infinity_story(
            problem=r"\lim_{x \to +\infty} \left(1 + \frac{3}{x}\right)^x", form=r"1^\infty",
            f=lambda x: (1 + 3 / x) ** x, L=math.exp(3), L_label=r"e^3",
            x_range=[0, 40, 10], y_range=[0, 22, 5], x_numbers=[10, 20, 30, 40], y_numbers=[5, 10],
            x_start=0.5, plot_from=0.05, decimals=2,
            algebra=[
                ("rewrite", [r"\left(1 + \frac{3}{x}\right)^x = \left[\left(1 + \frac{3}{x}\right)^{\frac{x}{3}}\right]^3"]),
                ("e", [r"(1 + u)^{\frac{1}{u}} \xrightarrow[u \to 0]{} e, \quad u = \frac{3}{x}"]),
            ],
            answer=r"\lim_{x \to +\infty} \left(1 + \frac{3}{x}\right)^x = e^3 \approx 20.09",
        )
