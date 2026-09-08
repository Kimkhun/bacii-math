#!/usr/bin/env python3
"""Verify the 2018 BAC II math exam extraction end to end.

For every one of the exam's 7 questions (all 7 sections, ~25 gradable
sub-parts): solve it through the live engine (``engine.core.dispatch.solve``)
and compare the result to the value transcribed from the teacher's own
worked solution (2018_Question.pdf, pages 2-6) — then grade a correct and an
incorrect sample answer through ``engine.core.grading.grade_part`` to prove
the deterministic grader, not just the solver, works.

Question 2 (limits) is already live in engine/topics/limit/data/curated/
(ids 2018a/b/c) from a prior extraction pass; this script re-solves it with
the same expressions to confirm nothing regressed. Questions 1, 3, 5, 7 are
the new ``past_exam`` topic (engine/topics/past_exam/); questions 4 and 6
reuse the existing ``integral`` and ``differential_equations`` topics
directly with this exam's own numbers.

Also demonstrates the deterministic step-by-step marking scheme
(engine/topics/past_exam/rubric.py): a full-work marking pass over a
simulated student answer sheet for every question, printing the per-step
point breakdown out of the paper's real total (125 = 10+15+15+15+25+10+35,
split as given), to show partial credit actually working (not just a
correct/incorrect final answer).

Run from the repo root:  python scripts/verify_past_exam_2018.py
"""
import os
import sys

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))

from sympy import Rational, latex, log, oo, pi, simplify, sympify  # noqa: E402

from engine.core.dispatch import solve  # noqa: E402
from engine.core.grading import grade_part  # noqa: E402

PASS, FAIL = [], []


def check_value(name, topic, question_type, params, label, expected_str):
    sol = solve(topic, question_type, params)
    if label is None:
        got = sol["answer_exact"]
    else:
        part = next(p for p in sol["parts"] if p["label"] == label)
        got = part["answer_exact"]
    expected = sympify(expected_str, locals={"log": log, "pi": pi, "oo": oo})
    ok = False
    try:
        ok = got == expected or simplify(got - expected) == 0
    except TypeError:
        ok = list(got) == list(expected) if hasattr(expected, "__iter__") else False
    (PASS if ok else FAIL).append(f"{name}: got {got}, expected {expected}")
    print(f"{'PASS' if ok else 'FAIL'}  {name:40s} got={got!s:30s} expected={expected!s}")


def check_grade(name, topic, question_type, params, label, user_answer, expect_correct):
    verdict = grade_part(topic, question_type, params, label, user_answer)
    ok = verdict["correct"] == expect_correct
    (PASS if ok else FAIL).append(f"{name}: grade_part({user_answer!r}) -> {verdict['correct']}")
    tag = "PASS" if ok else "FAIL"
    print(f"{tag}  {name:40s} grade_part({user_answer!r}) -> correct={verdict['correct']} (expected {expect_correct})")


def main():
    print("=== Question I: probability/counting ===")
    q1 = {"white": 2, "red": 4, "blue": 4, "draw": 3}
    check_value("I.A P(A)=1/30", "past_exam", "2018_q1", q1, "A", "1/30")
    check_value("I.B P(B)=1/3", "past_exam", "2018_q1", q1, "B", "1/3")
    check_value("I.C P(C)=4/15", "past_exam", "2018_q1", q1, "C", "4/15")
    check_grade("I.A grade correct", "past_exam", "2018_q1", q1, "A", "1/30", True)
    check_grade("I.B grade wrong", "past_exam", "2018_q1", q1, "B", "1/2", False)

    print("\n=== Question II: limits (already live: engine/topics/limit/data/curated) ===")
    check_value("II.a lim = -2", "limit", "limit",
                {"var": "x", "expr": "(x**2*(x-2)+x**2+x-1)/(1-x)", "point": "1"}, None, "-2")
    check_value("II.b lim = -2/3", "limit", "limit",
                {"var": "x", "expr": "-2*x/sin(3*x)", "point": "0"}, None, "-2/3")
    check_value("II.c lim = -1/3", "limit", "limit",
                {"var": "x", "expr": "(sin(x)-sqrt(3)*cos(x))/(2*(pi-3*x))", "point": "pi/3"}, None, "-1/3")

    print("\n=== Question III: complex numbers (irrational coefficients) ===")
    q3 = {"z1_re": "3", "z1_im": "3*sqrt(3)", "z2_re": "sqrt(3)", "z2_im": "1"}
    check_value("III.a1 z1*z2=12i", "past_exam", "2018_q3", q3, "a1", "12*I")
    check_value("III.a2 z1/z2", "past_exam", "2018_q3", q3, "a2", "3*sqrt(3)/2+3*I/2")
    check_value("III.b2 (z1/z2)^2", "past_exam", "2018_q3", q3, "b2", "9/2+9*sqrt(3)*I/2")
    check_value("III.c1 (z1/z2)^3=27i", "past_exam", "2018_q3", q3, "c1", "27*I")
    check_grade("III.a1 grade correct", "past_exam", "2018_q3", q3, "a1", "12*I", True)
    check_grade("III.c1 grade wrong", "past_exam", "2018_q3", q3, "c1", "27", False)

    print("\n=== Question IV: integrals ===")
    check_value("IV.I = 17/6", "integral", "definite_integral",
                {"var": "x", "expr": "2-x+x**2", "lower": "1", "upper": "2"}, None, "17/6")
    check_value("IV.J = 1/2", "integral", "definite_integral",
                {"var": "x", "expr": "cos(2*x)-cos(4*x)/2", "lower": "0", "upper": "pi/4"}, None, "1/2")
    check_value("IV.K = 11/2+ln2", "integral", "definite_integral",
                {"var": "x", "expr": "3*x-2+1/(x-1)", "lower": "2", "upper": "3"}, None, "11*Rational(1,2)+log(2)")

    print("\n=== Question V: 3D vectors + conic ===")
    q5v = {"A": [1, 2, 3], "B": [3, 0, 1], "C": [-1, 0, 1], "D": [2, 1, 2], "n": [0, 1, -1]}
    check_value("V.AB=(2,-2,-2)", "past_exam", "2018_q5_vectors", q5v, "AB", "(2,-2,-2)".replace("(", "[").replace(")", "]"))
    check_value("V.cross=(0,8,-8)", "past_exam", "2018_q5_vectors", q5v, "cross", "[0,8,-8]")
    check_value("V.n.AB=0", "past_exam", "2018_q5_vectors", q5v, "n_dot_AB", "0")
    check_value("V.n.AC=0", "past_exam", "2018_q5_vectors", q5v, "n_dot_AC", "0")
    check_grade("V.AB grade correct", "past_exam", "2018_q5_vectors", q5v, "AB", "(2,-2,-2)", True)
    check_grade("V.AB grade wrong", "past_exam", "2018_q5_vectors", q5v, "AB", "(2,-2,-3)", False)

    q5c = {"expr": "(2*x+3*y)**2 - 12*(x*y+3)"}
    check_value("V.a=3", "past_exam", "2018_q5_conic", q5c, "a", "3")
    check_value("V.b=2", "past_exam", "2018_q5_conic", q5c, "b", "2")
    check_value("V.V1=(-3,0)", "past_exam", "2018_q5_conic", q5c, "v1", "[-3,0]")
    check_value("V.V2=(3,0)", "past_exam", "2018_q5_conic", q5c, "v2", "[3,0]")
    check_grade("V.V1 grade correct", "past_exam", "2018_q5_conic", q5c, "v1", "(-3,0)", True)

    print("\n=== Question VI: differential equation ===")
    q6 = {"kind": "second_order_homogeneous_constant_coeff", "b": 4, "c": -5,
          "ics": {"x0": 0, "y0": 3, "yp0": -3}}
    check_value("VI. y = 2e^x+e^-5x", "differential_equations", "solve_ode", q6, None,
                "2*exp(x)+exp(-5*x)")

    print("\n=== Question VII: function study (restricted domain x>1) ===")
    q7 = {"expr": "-x+4+log((x+1)/(x-1))", "domain_lo": "1", "tangent_slope": "-5/3"}
    check_value("VII.k1 lim@1+ = +oo", "past_exam", "2018_q7", q7, "k1", "oo")
    check_value("VII.k2 lim@+oo = -oo", "past_exam", "2018_q7", q7, "k2", "-oo")
    check_value("VII.kh_der f'(x)", "past_exam", "2018_q7", q7, "kh_der", "-(x**2+1)/((x+1)*(x-1))")
    check_value("VII.kot1 d1: y=-x+4", "past_exam", "2018_q7", q7, "kot1", "-x+4")
    check_value("VII.kh_tan d2", "past_exam", "2018_q7", q7, "kh_tan", "-5*x/3+16/3+log(3)")
    check_grade("VII.k1 grade correct", "past_exam", "2018_q7", q7, "k1", "oo", True)
    check_grade("VII.kh_mono grade correct", "past_exam", "2018_q7", q7, "kh_mono",
                "f is decreasing on (1, +infinity)", True)
    check_grade("VII.kot2 grade correct", "past_exam", "2018_q7", q7, "kot2", "C is above d1", True)
    check_grade("VII.kot2 grade wrong", "past_exam", "2018_q7", q7, "kot2", "C is below d1", False)

    print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed.")
    if FAIL:
        print("FAILURES:")
        for f in FAIL:
            print(" -", f)
        sys.exit(1)

    demo_marking_scheme()


def demo_marking_scheme():
    """Run the deterministic step-by-step marking scheme (rubric.py) over a
    SIMULATED student answer sheet — deliberately imperfect in a few places
    (a skipped intermediate step, a wrong final value, an out-of-order
    write-up, a missed qualitative verdict) — to demonstrate partial credit,
    not just a pass/fail check. This section has no PASS/FAIL of its own;
    it is illustrative."""
    from engine.topics.past_exam.rubric import mark_full_exam

    params_by_question = {
        1: {"white": 2, "red": 4, "blue": 4, "draw": 3},
        2: {},
        3: {"z1_re": "3", "z1_im": "3*sqrt(3)", "z2_re": "sqrt(3)", "z2_im": "1"},
        4: {},
        5: {"A": [1, 2, 3], "B": [3, 0, 1], "C": [-1, 0, 1], "D": [2, 1, 2], "n": [0, 1, -1]},
        6: {},
        7: {"expr": "-x+4+log((x+1)/(x-1))", "domain_lo": "1", "tangent_slope": "-5/3"},
    }
    # A simulated student's written work, one asserted fact per line. Not
    # exam-perfect on purpose: Q1 skips n(B) and gets P(C) wrong; Q3 skips
    # the trig-form of (z1/z2)^2; Q7 writes the wrong monotonicity verdict.
    lines_by_question = {
        1: ["n(S) = 120", "n(A) = 4", "P(A) = 1/30",
            "P(B) = 1/3", "n(C) = 32", "P(C) = 1/2"],
        2: ["(x-1)*(x**2+1)/(1-x) = -x**2-1", "lim = -2",
            "lim 3*x/sin(3*x) = 1", "lim = -2/3",
            "lim sin(t)/t = 1", "lim = -1/3"],
        3: ["z1*z2 = 12*I", "z1/z2 = 3*sqrt(3)/2+3*I/2",
            "z1*z2 = 12*(cos(pi/2)+I*sin(pi/2))", "(z1/z2)**3 = 27*I"],
        4: ["F(x) = 2*x-x**2/2+x**3/3", "I = 17/6",
            "F(x) = sin(2*x)/2-sin(4*x)/8", "J = 1/2",
            "F(x) = 3*x**2/2-2*x+log(x-1)", "K = 11/2+log(2)"],
        5: ["AB = (2,-2,-2)", "AC = (-2,-2,-2)", "AD = (1,-1,-1)", "BC = (-4,0,0)",
            "AB x AC = (0,8,-8)", "n.AB = 0", "n.AC = 0",
            "a = 3", "b = 2", "V1 = (-3,0)", "V2 = (3,0)"],
        6: ["r1 = 1", "r2 = -5", "C1 = 2", "C2 = 1", "y = 2*exp(x)+exp(-5*x)"],
        7: ["lim = oo", "lim = -oo", "f'(x) = -(x**2+1)/((x+1)*(x-1))",
            "f is increasing on (1,+infinity)",  # wrong verdict, on purpose
            "d1: y = -x+4", "C is above d1",
            "x0 = 2", "d2: y = -5*x/3+16/3+log(3)"],
    }

    result = mark_full_exam("2018", params_by_question, lines_by_question)
    print("\n=== Marking-scheme demonstration (simulated, imperfect answer sheet) ===")
    for q, res in sorted(result["per_question"].items()):
        pct = float(res["earned"]) / float(res["possible"]) * 100 if res["possible"] else 0
        print(f"\nQuestion {q}: {res['earned']} / {res['possible']}  ({pct:.1f}%)")
        for b in res["breakdown"]:
            tag = "OK  " if b["points_earned"] > 0 else "MISS"
            print(f"  {tag} {b['item']:12s} {b['label']:38s} "
                  f"{float(b['points_earned']):5.2f} / {float(b['points_possible']):5.2f}"
                  + (f"   <- {b['matched_line']!r}" if b["matched_line"] else ""))
    pct = float(result["earned"]) / float(result["possible"]) * 100
    print(f"\nTOTAL: {result['earned']} / {result['possible']}  ({pct:.1f}%)")


if __name__ == "__main__":
    main()
