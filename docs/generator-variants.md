# Generator variant catalog (reference)

Every question template the generator can emit, which formulas it tags, and
which difficulty pools it belongs to. Derived from `backend/engine/generator.py`
(`_INTEGRAL_VARIANT_BY_DIFFICULTY`, `_INDEFINITE_VARIANT_BY_DIFFICULTY`,
`_LIMIT_VARIANT_BY_DIFFICULTY`, complex pools).

## Complex numbers (5 question types; pools pick random params)

| Question type | Parameterization | Tags |
|---|---|---|
| modulus | Pythagorean-triple pools per difficulty + random signs | `pythagorean`, `sqrt_simplify` |
| argument | k per difficulty + 8 sign/quadrant combos | `atan2_ratio`, `quadrant_adjustment` |
| conjugate / real_part / imaginary_part | random a, b ∈ range (b ≠ 0) | `sign_flip` / `extract_real` / `extract_imag` |

Gemini mode (complex only): LLM proposes a,b + type; SymPy validates.

## Limits (variant fixed per difficulty)

| Difficulty | Variant | Tags |
|---|---|---|
| easy | polynomial (random coeffs + point) | `direct_substitution` |
| medium | removable `(x²−c²)/(x−c)` | `factor_difference_of_squares`, `cancel_common_factor`, `direct_substitution` |
| hard | infinity rational | `divide_highest_power`, `leading_coefficient_ratio` |

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