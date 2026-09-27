# Trigonometric Limit Solver Architecture & Strategy Synthesis

> **Status**: Approved Strategy (Implementing Procedural Algebraic Synthesis)  
> **Date**: 2026-09-27  
> **Topic**: Limits / Trigonometric Indeterminate Forms ($0/0$)  
> **Reference**: Cambodian Grade 12 Advanced Math Textbook (Mith Sakhon & Siv Sivanden, pp. 79–82) and BAC II National Exams (2014–2025)

---

## 1. Problem Statement & Motivation

### The Issue with Generic Fallbacks
Previously, the deterministic limit solver in `backend/engine/topics/limit/solver.py` handled trigonometric limits using a 4-line placeholder when `expr.has(sin)` was detected:
```python
# Old crude placeholder in solver.py:
steps.append(_limit_step(
    "Divide by the variable to isolate fundamental trigonometric limits",
    rf"\[ \dfrac{{{latex(num)}}}{{{latex(den)}}} = \dfrac{{\frac{{{latex(num)}}}{{{var}}}}}{{\frac{{{latex(den)}}}{{{var}}}}} \]",
    "limit_sin_x_over_x",
))
```
This produced nonsensical, redundant fraction nests like:
$$\frac{4\sin x - \sin 3x + \sin 4x}{x} = \frac{\frac{4\sin x - \sin 3x + \sin 4x}{x}}{\frac{x}{x}}$$
or
$$\frac{\sin 2x \sin 3x \sin 6x}{x^3} = \frac{\frac{\sin 2x \sin 3x \sin 6x}{x}}{\frac{x^3}{x}}$$
followed by an abrupt jump to the numeric answer accompanied by English boilerplate text.

### The Question: Why Not Just Use an LLM?
* **LLM Arithmetic & Step Hallucination**: Generative models frequently drift, drop negative signs, miscalculate intermediate products (e.g. evaluating $2 \times 3 \times 6 = 32$), or invent invalid identities.
* **Deterministic CAS Ground Truth**: Under the system architecture protocol (`AGENTS.md`), SymPy is the deterministic ground truth. Intermediate step checkpoints must have exact, verifiable algebraic values so line-by-line student grading (`analyze_work`) can verify student work deterministically.

---

## 2. The 4 Universal Algebraic Strategies

Rather than hardcoding an infinite number of one-off chains, every exercise in the Cambodian Grade 12 curriculum falls into one of **4 Canonical Mathematical Strategies**:

```
                       Trigonometric Indeterminate Limit (0/0)
                                      |
       +-----------------------+------+-----------------------+
       |                       |                              |
[1. Sum Splitter]      [2. Product Splitter]        [3. Half-Angle / Conjugate]
  Sum of sines /         Product of sines /           Forms with 1 - cos(kx)
  tans over x^n          tans over x^n                or 2 - cos(ax) - cos(bx)
  (Exercises A, C, D, I) (Exercises B, E)             (Exercises F, G, H)
                                                              |
                                                    [4. Identity Reducer]
                                                      Special identities
                                                      (tan 3x, angle addition)
                                                      (Exercise J, 2018c, 2025d)
```

### Strategy 1: The Sum Splitter (`_solve_sinc_sum_strategy`)
* **Input**: Expression $\frac{\sum_{i=1}^m c_i \sin(k_i x)}{x}$ or $\frac{\sum_{i=1}^m c_i f(k_i x)}{d \cdot x^p}$
* **Step 1 (Indeterminate Form)**:
  $$\lim_{x\to 0} \frac{\sum c_i \sin(k_i x)}{x} \quad \text{មានរាងមិនកំណត់ } \frac{0}{0}$$
* **Step 2 (Term Separation)**:
  $$= \sum_{i=1}^m \lim_{x\to 0} \frac{c_i \sin(k_i x)}{x}$$
* **Step 3 (Argument Normalization)**:
  $$= \sum_{i=1}^m c_i \cdot k_i \lim_{x\to 0} \frac{\sin(k_i x)}{k_i x}$$
* **Step 4 (Fundamental Limit Evaluation)**:
  $$= \sum_{i=1}^m c_i \cdot k_i (1) = \text{result}$$
  $$\text{ដូចនេះ } \lim_{x\to 0} \dots = \text{result} \text{ ។}$$

### Strategy 2: The Product Splitter (`_solve_sinc_product_strategy`)
* **Input**: Expression $\frac{\prod_{i=1}^m \sin^{p_i}(k_i x)}{K \cdot x^N \cdot \prod \sin(m_j x)}$ where powers of $x$ match total numerator sine powers.
* **Step 1 (Indeterminate Form)**: Form $\frac{0}{0}$.
* **Step 2 (Denominator Distribution)**: Distribute each factor of $x$ to its respective sine term:
  $$= \prod_{i=1}^m \lim_{x\to 0} \frac{\sin(k_i x)}{x}$$
* **Step 3 (Argument Normalization)**: Factor out $k_i$:
  $$= \prod_{i=1}^m k_i \lim_{x\to 0} \frac{\sin(k_i x)}{k_i x}$$
* **Step 4 (Final Product)**:
  $$= \prod_{i=1}^m k_i = \text{result}$$

### Strategy 3: The Half-Angle / Cosine Pairer (`_solve_cos_half_angle_strategy`)
* **Input**: Expression $\frac{C - \sum c_i \cos(k_i x)}{x^2}$
* **Sub-case A (Simple Half-Angle)**: $\frac{1 - \cos(kx)}{x^2} = \frac{2\sin^2(kx/2)}{x^2}$
* **Sub-case B (Paired Half-Angles)**: Split constant $2 = 1 + 1$ or $1 = 3 - 2$:
  $$\frac{2 - \cos(ax) - \cos(bx)}{x^2} = \frac{1 - \cos(ax)}{x^2} + \frac{1 - \cos(bx)}{x^2}$$
* **Sub-case C (Difference of Cubes)**: $1 - \cos^3(kx) = (1 - \cos kx)(1 + \cos kx + \cos^2 kx)$
* **Evaluation**: Convert to sinc squared limits and compute $(k/2)^2 \times 2$.

### Strategy 4: The Identity Reducer (`_solve_trig_identity_strategy`)
* **Sub-case A (Tangent Triple Angle)**: Use $\tan 3x = \frac{3\tan x - \tan^3 x}{1 - 3\tan^2 x}$
  $$3\tan x - \tan 3x = \frac{3\tan x(1 - 3\tan^2 x) - (3\tan x - \tan^3 x)}{1 - 3\tan^2 x} = \frac{-8\tan^3 x}{1 - 3\tan^2 x}$$
  Dividing by $x^3$ yields $-8 \times 1^3 = -8$.
* **Sub-case B (Angle Addition Identity)**: $\sin x - \sqrt{3}\cos x = 2\sin(x - \pi/3)$

---

## 3. Technical Debt Assessment & Mitigations

| Risk Factor | Assessment | Mitigation in Place |
| :--- | :--- | :--- |
| **Complexity Growth** | Low (bounded by curriculum scope) | The Grade 12 BAC II syllabus contains a closed set of algebraic patterns. No new algebraic techniques exist outside these 4 strategies. |
| **Maintenance Burden** | Very Low | Handlers take parameterized variables from SymPy `slots`. Code changes only touch `solver.py`, while template generator draws randomly. |
| **Drift from Textbook** | Zero | Derivation chains directly mirror Mith Sakhon & Siv Sivanden pages 79–82. |
| **LLM Reliability** | Eliminated | No probabilistic text models are in the solving loop. Grading and step derivation remain 100% deterministic. |

---

## 4. UI & Typography Rules for Solvers

1. **Khmer vs. KaTeX Segregation**:
   * Titles use native browser Khmer typography (e.g. `ទម្រង់មិនកំណត់ 0/0`, `បំបែកតួនៃប្រភាគ`, `កែសម្រួលមុំតាមរូបមន្តគ្រឹះ`, `គណនាតម្លៃចុងក្រោយ`).
   * Mathematical formulas are enclosed in clean LaTeX blocks (`\[ ... \]` or `\( ... \)`).
   * Never wrap Khmer phrases inside `\text{...}` inside KaTeX to prevent font bounding-box leaks.
2. **Standard Conclusion Tag**:
   * Conclude with authentic Cambodian style: `\text{ដូចនេះ } \dots = \text{result} \text{ ។}`
