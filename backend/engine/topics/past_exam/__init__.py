"""Past-exam topic: verbatim replay of real, previously-graded BAC II exam
papers (as opposed to every other topic, which generates a fresh instance
from a technique template). This is the "source='exam', playing an exercise
verbatim" mode flagged as a future item in docs/exam-data.md.

Most of a given past exam's questions already fit an existing topic's
generic solver (limits/integrals are plain expr+point/bounds; a "solve the
ODE with these initial conditions" or "study this function" question slots
straight into differential_equations/functions) — those are wired directly
in the exam's manifest (``data/curated/<year>.json`` entries whose own
``topic``/``question_type`` point elsewhere) and never touch this module.
This topic's ``solver.py`` only carries the handful of question shapes no
existing topic covers:

  q1  three-color hypergeometric counting/probability word problem
      (existing ``probability`` topic's "hypergeometric" structure is
      2-color only)
  q3  complex arithmetic/trig-form on numbers with irrational (sqrt)
      coefficients (existing ``complex`` topic is plain-integer a+bi only)
  q5  3D vector components as a graded vector/point value, and a conic
      derived from a general-form equation down to its standard-form
      constants (the existing ``conics`` topic classifies conics but this
      exercise's deliverable is the raw vertex coordinates)
  q7  full function study on a domain the exam *restricts by fiat*
      (x>1) rather than one derivable from the expression alone (the
      existing ``functions`` topic derives domain/monotonicity from
      ``expr.as_numer_denom()``, which only works when the whole
      function_expr is a bare log or a bare rational — not a
      polynomial-plus-log sum like this one)

``solver.py`` computes every answer with SymPy; ``generator.py`` replays a
verbatim exam question from ``data/curated/<year>.json`` (no randomization —
the numbers ARE the historical exam); ``grader.py`` has no custom rule.
"""
