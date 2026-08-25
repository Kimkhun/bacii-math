# Generator variant catalog (reference)

Every question template the generator can emit, which formulas it tags, and
which difficulty pools it belongs to. Derived from `backend/engine/generator.py`
(`_INTEGRAL_VARIANT_BY_DIFFICULTY`, `_INDEFINITE_VARIANT_BY_DIFFICULTY`,
`_LIMIT_VARIANT_BY_DIFFICULTY`, complex pools).

## Complex numbers (9 question types; pools pick random params)

| Question type | Parameterization | Tags |
|---|---|---|
| modulus | Pythagorean-triple pools per difficulty + random signs | `pythagorean`, `sqrt_simplify` |
| argument | k per difficulty + 8 sign/quadrant combos | `atan2_ratio`, `quadrant_adjustment` |
| conjugate / real_part / imaginary_part | random a, b ∈ range (b ≠ 0) | `sign_flip` / `extract_real` / `extract_imag` |
| complex_arithmetic | random z1, z2; operation ∈ {add, subtract, multiply, divide} by difficulty (`solver/complex/arithmetic.py`) | `complex_addition` / `_subtraction` / `_multiplication` / `_division` |
| complex_power | random z = a+bi; fixed small n (2/3/4 by difficulty), direct binomial expansion — not De Moivre (`solver/complex/power.py`) | `binomial_expansion_i_squared` |
| de_moivre_power | z built from a "nice" (r, standard-angle) pair (`solver/complex/trig.py`'s 16-angle pool, multiples of 30°/45°) so z itself looks like a real textbook number (e.g. `2+2i√3`); n scales by difficulty, capped so `r^n ≤ 10^18` (kept displayable/gradable — the real exam's huge exponents like `(1-i)^2021` only stay tractable if left in unexpanded power form, which this app's plain-value grading doesn't support yet) (`solver/complex/de_moivre.py`) | `trig_form_conversion`, `de_moivre_formula`, `angle_reduction_mod_2pi`, `trig_to_algebraic` |
| nth_roots | reverse-built: pick the *answer* root w from the same standard-angle pool, then present z = w^n as the given number; n by difficulty (2/2-3/3-5) (`solver/complex/nth_roots.py`) | `trig_form_conversion`, `nth_root_formula`, `trig_to_algebraic` |

Gemini mode (complex only, classic 5 types only): LLM proposes a,b + type; SymPy validates.

**Curated textbook exercises:** each `easy`-difficulty request for `modulus`,
`argument`, `conjugate`, `real_part`, or `imaginary_part` has a 50% chance of
drawing a curated textbook exercise instead, if one exists for that exact
question type (`generator/complex._generate_templates`). The curated pool
(`engine/structures._COMPLEX_CURATED_TEMPLATES`) is parsed at import time from
`backend/data/complex_numbers/{formula_name}.json` — only the subset of
textbook exercises posed as a literal `z = a+bi` (plain integers, no
powers/radicals) round-trips through the existing a+bi solver, so the curated
pool is intentionally small (6 exercises as of 2026-08-25). SymPy still
computes/grades the answer identically to the procedural pool — the curated
item only supplies the a, b pair and an exam-authored `curated_technique` note
for reference. The 4 new question types above are procedural-only for now (no
curated pool wired in yet).

**Still not templated** (of the 164 textbook exercises in
`backend/data/complex_numbers/`, these categories have no solver yet — see
`exam-data.md`): standalone "write z in trig form" as its own multi-part
exercise (`trig_form_conversion.json`, `quotient_trig_form.json` — the trig
form *value* is already reachable via modulus+argument, but grading the (r, θ)
pair as two separate blanks needs multi-part grading like probability's
`grade_multi`, not yet wired for topic `complex`), solving equations in z/z̄
(`complex_equations.json`), classifying geometric loci
(`locus_equations.json`), plotting affixes (`geometric_representation.json`),
and the symmetric-sum/Vieta root-of-unity identities
(`roots_of_unity.json`'s proof-style problems — `nth_roots` above only covers
"find a root", not those).

## Limits

Each request has a 50% chance of drawing a **curated** exercise (one of the 56
real BAC II / textbook limit questions, sorted by technique into
`backend/data/limits/{formula_name}.json`) for the given difficulty, falling
back to the procedural variant otherwise. Curated params carry `formula_name`
+ the exam-authored technique text (`engine/structures._LIMIT_CURATED_TEMPLATES`,
parsed at import time); `solver._solve_limit`'s `formula_name` branch uses that
text to narrate steps while SymPy still computes/grades the answer.

| Difficulty | Procedural variant | Procedural tags | Curated formula names (SymPy-verified) |
|---|---|---|---|
| easy | polynomial (random coeffs + point) | `direct_substitution` | `direct_substitution`, `factoring_0_0` |
| medium | removable `(x²−c²)/(x−c)` | `factor_difference_of_squares`, `cancel_common_factor`, `direct_substitution` | `rationalization_conjugate_finite`, `trig_identity_0_0`, `sinc_standard_limit`, `angle_addition_0_0`, `rationalization_sinc_combo`, `exponential_sinc_combo`, `half_angle_sinc_combo`, `exponential_standard_limit` |
| hard | infinity rational | `divide_highest_power`, `leading_coefficient_ratio` | `conjugate_infinity`, `log_limit_infinity`, `rational_function_infinity`, `log_limit_zero`, `indeterminate_one_infinity` |

(`log_limit_zero` and `indeterminate_one_infinity` are textbook-extracted
exercises, not exam questions — 20 items with SymPy-verified `answer_latex`
added when they were folded into `backend/data/limits/`; see `exam-data.md`.)

(One curated exercise, `2024b`, is excluded from the pool — it's an inverse
"find a given the limit" problem, not a plain limit to solve.)

## Definite integrals (`topic=integral`, `definite_integral`)

| Variant | Difficulty pool | Example | Tags (+`fundamental_theorem`) |
|---|---|---|---|
| polynomial | easy/medium | `∫3x²−2x−1 dx` over integers | `antiderivative_power_rule` |
| trig | hard | `c·sin x` / `c·cos x` over clean bounds | `antiderivative_trig` |
| linear_argument | medium | `∫sin(kx)`, `e^(kx+b)`, `(kx+b)ⁿ`, `1/(kx+b)`, `1/√(kx+b)` | `linear_argument_rule` |
| u_substitution | hard | `u = x²+c / x³+c / x²+ax+c`, trig-power, `lnⁿx/x`, `eˣ/(eˣ+c)`, sqrt forms | `u_substitution` |
| mixed_sum | medium | 2–3 term sums (algebraic+exp over integer bounds, or trig over special angles) | per-term (power/reciprocal/exponential/trig/trig_sec) |
| by_parts | hard | `x·sin(kx)`, `x·cos(kx)`, `x·eˣ`, `xⁿln x`, `ln²x/x` | `integration_by_parts` |

## Indefinite integrals (`indefinite_integral`)

| Variant | Difficulty pool | Example | Tags |
|---|---|---|---|
| power | easy | curated shapes / pure-power sums | per-term `antiderivative_power_rule` |
| expand | easy/medium/hard | `(ax+b)(cx−d)`, `(ax−b)²`, `ax(bx²+cx−d)`, … | `expand_before_integrating` + per-term |
| split | medium/hard | `(ax²+bx−c)/x`, `(…)/(2x²)`, `(…)/√x` | `split_fraction` + per-term |
| linear_argument | medium/hard | `sin(kx)`, `(kx+b)ⁿ`, `1/(kx−b)ⁿ`, `e^(kx+b)` | `linear_argument_rule` + per-term |
| usub | hard | 19 u'·f(u) shapes: x²+c, quadratic u, ln u, trig-powers, sqrt/cuberoot, e-linear | `u_substitution` + per-term |
| trig_sec | hard | random sums incl. `1/cos²x`, `2/sin²x` + special constants | per-term incl. `antiderivative_trig_sec` |

All answers are SymPy-exact; slots (`{a},{b},…,{n}`) are filled from positive
coefficient pools — sign variety comes from template structure.

## Probability (`topic=probability`, `question_type=probability`)

Scenarios come from the user-owned catalog `backend/data/scenarios/probability.json`
(loaded by `engine/scenarios.py`); the admin `/templates` inventory forces one row
per scenario id per difficulty. Answers are SymPy-exact fractions.

| Difficulty | Scenarios (catalog ids) | Tags |
|---|---|---|
| easy | `urn_exactly_split_easy`, `urn_all_white`, `urn_all_black`, `two_box_both_white`, `two_box_both_black`, `two_box_cross`, `two_box_one_white` | `hypergeometric_rule`(+`combination_rule`) / `laplace_rule`+`product_rule`(+`union_rule`) |
| medium | `urn_exactly_split_med`, `urn_at_least_one`, `two_bag_all_odd`, `two_bag_all_even`, `two_bag_at_least_odd` | `hypergeometric_rule`+`combination_rule`(+`complement_rule`) / `combination_rule`+`product_rule` |
| hard | `urn_exactly_split_hard`, `urn_exactly_split_students` | `hypergeometric_rule`+`combination_rule` |

Structures with no catalog scenarios yet (solver-ready, awaiting real frames):
`laplace` (single draw), `binomial` (coins), `union`, `conditional`.

## Admin inventory

`GET /templates` forces every variant per difficulty (deterministic seed per
row) — the authoritative live view of this table. `GET /formulas` lists the
registry (built-ins + `backend/data/formulas/*.json` overlays, incl. the 8
probability techniques) with names/latex/weights/formulas.