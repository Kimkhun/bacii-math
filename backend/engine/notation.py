"""Turns the plain SymPy-parseable expression strings used internally (e.g. "3*x**2-4*x")
into standard math notation for display to students (e.g. "3x² - 4x"). Purely cosmetic —
never touches the strings actually passed to SymPy for solving/grading.
"""
import re

_SUPERSCRIPT = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")

_POINT_DISPLAY = {"oo": "+∞", "-oo": "-∞"}


def _superscript(exponent: str) -> str:
    return exponent.translate(_SUPERSCRIPT)


def pretty_expr(expr: str) -> str:
    s = expr
    s = re.sub(r"-\s*-", "+ ", s)
    s = re.sub(r"\*\*(-?\d+)", lambda m: _superscript(m.group(1)), s)
    s = re.sub(r"(?<=[\w)])\*(?=[\w(])", "", s)
    s = re.sub(r"\bsqrt\(", "√(", s)
    s = re.sub(r"\bpi\b", "π", s)
    s = re.sub(r"\boo\b", "∞", s)
    s = s.replace("+-", "- ").replace("+ -", "- ")
    s = re.sub(r"(?<=[0-9)])-", " - ", s)
    s = re.sub(r"(?<=[0-9)])\+", " + ", s)
    return s


def pretty_point(point: str) -> str:
    return _POINT_DISPLAY.get(point, pretty_expr(point))
