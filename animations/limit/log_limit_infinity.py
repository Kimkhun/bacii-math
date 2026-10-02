"""Log limit at infinity: x ln(1 + 2/x) = 2 ln(1+u)/u with u = 2/x."""
import math

from common.limit_kit import LimitScene


class Lesson(LimitScene):
    lesson_id = "log_limit_infinity"

    def construct(self):
        self.check("x*(log(x + 2) - log(x))", "oo", 2)
        self.infinity_story(
            problem=r"\lim_{x \to +\infty} x\left[\ln(x + 2) - \ln x\right]", form=r"\infty \cdot 0",
            f=lambda x: x * math.log(1 + 2 / x), L=2, L_label="2",
            x_range=[0, 40, 10], y_range=[0, 3, 1], x_numbers=[10, 20, 30, 40], y_numbers=[1],
            x_start=0.5, plot_from=0.02,
            algebra=[
                ("combine", [r"x\left[\ln(x + 2) - \ln x\right] = x \ln\left(1 + \frac{2}{x}\right)"]),
                ("substitute_u", [r"= 2 \cdot \frac{\ln(1 + u)}{u}, \quad u = \frac{2}{x} \to 0^+"]),
            ],
            answer=r"\lim_{x \to +\infty} x\left[\ln(x + 2) - \ln x\right] = 2 \cdot 1 = 2",
        )
