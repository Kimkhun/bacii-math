# Khmer / English language mode

How the app shows a Cambodian student the whole product — interface, exercise
statements, grading verdicts and step-by-step explanations — in Khmer, and how
to keep it that way when adding a topic, a question type or a screen.

The guiding split is that **the math never gets translated, only the words
around it**. SymPy remains the single source of truth (see CLAUDE.md); nothing
in this feature computes, re-checks or re-words a mathematical result. A
language toggle that could change an answer would be a bug, not a feature.

## Where each kind of text comes from

Text on screen falls into four buckets, and each one is localized in a
different place. Knowing which bucket a string is in tells you where to fix it.

| Bucket | Example | Localized in | Language chosen |
|---|---|---|---|
| **Interface chrome** | "New question", "Accuracy", "Needs revision" | `web/src/lib/i18n.ts` → `TRANSLATIONS` | Client, instantly |
| **Exercise statement** | "Find the modulus \|z\| of z = −12 + 5i." | `web/src/lib/i18n.ts` → `formatLocalizedPrompt()` | Client, instantly |
| **LLM prose** | the friendly explanation, the work-check, the teacher's rubric tip | `backend/engine/llm.py` prompts | Server, per request (`lang`) |
| **Deterministic explanation** | the SymPy step list used when the LLM is unavailable | `backend/engine/explainer.py` | Server, per request (`lang`) |

The first two are client-side on purpose. A student toggling to Khmer re-renders
the page they are already on — no refetch, no regenerated question, no lost
handwriting. It also means **generation is language-neutral**: `POST
/problems/generate` deliberately has no `lang` field, because the problem SymPy
builds is the same problem in either language and only its *rendering* differs.
`GradeRequest` and `ExplainRequest` do carry `lang`, because those produce prose.

## The client

### `LanguageContext`

`web/src/context/LanguageContext.tsx` holds `lang` (`"en" | "km"`), persists it
to `localStorage["bacii_lang"]`, and exposes `t(key)` for interface strings.
Every localized page and `Navbar` consume it through `useLanguage()`. Called
outside the provider it degrades to English rather than throwing, so a stray
component can never blank the page.

State starts at the server-rendered `"en"` and resolves in a mount effect.
That ordering is deliberate: initialising from `localStorage` in `useState`
would make the first client render disagree with the SSR HTML. To stop the
document itself being mislabelled for that frame, a small inline script in
`app/layout.tsx` sets `<html lang>` from `localStorage` **before first paint**,
so fonts and screen-reader pronunciation are right immediately. The rendered
strings still swap during hydration; removing that last flash would mean
rendering the app client-only and giving up static HTML on the public pages,
which is not a trade worth making for one frame.

### `TRANSLATIONS`

A flat `Record<Language, Translations>` with **186 keys**, where `Translations`
is an explicit interface rather than an inferred type. That interface is the
enforcement mechanism: a key added to `en` and forgotten in `km` fails
`tsc`, so the two dictionaries cannot drift. Keep it that way — do not loosen
it to `Record<string, string>`.

`QUESTION_TYPE_LABELS` is separate and shaped differently: a flat
`Record<string, { en, km }>` of **43 entries**, keyed by `question_type` or
`question_type:variant` — the same encoding the practice page's type dropdown
and `engine/core/skills.py` already use, so a key round-trips between them.
Pairing both languages inside one entry is what keeps a label from existing in
only one language.

### `formatLocalizedPrompt()`

Turns a generated question into a Khmer statement. It is a pure function of what
the API already returns — `topic`, `question_type`, `params`, `prompt`,
`prompt_latex`, `z_display` — so it never needs a round trip.

Its contract, in order:

1. **English, or no params → return the original.** Nothing to do.
2. **Statement already Khmer → return it unchanged.** Probability scenarios,
   function studies and past-exam papers are authored in Khmer upstream
   (`engine/topics/probability/scenarios.py`, `data/curated/`), so the check is
   simply "does `rawPrompt` contain Khmer script".
3. **Otherwise rebuild the statement per topic** from `params`.

Rule 3 has one hard invariant, and it is the reason this function is worth
testing rather than eyeballing:

> **A localized statement must never contain less information than the English
> one.** Every number, operand and exponent in the original has to survive.

A Khmer prompt that drops the numbers is worse than an untranslated one — the
student cannot answer it at all. So every branch either reconstructs the full
statement or falls back to `rawPrompt`; no branch is allowed to emit a bare
template. Concretely, for complex numbers:

| Question type | Rebuilt from |
|---|---|
| `modulus`, `argument`, `conjugate`, `real_part`, `imaginary_part` | `params.a` / `params.b` |
| `complex_arithmetic` | `a1/b1`, `a2/b2` + `operation` |
| `complex_power` | `a`/`b` + `n` |
| `de_moivre_power`, `nth_roots` | the number extracted from `prompt_latex` + `n` |

The last row is why `latexGiven()` exists. The polar templates have no `a`/`b`
pair to rebuild from, and their `z_display` is plain text (`27sqrt(2)(-1 - i)/2`)
that renders as literal italic letters inside `$…$`. `prompt_latex` carries the
real LaTeX (`\frac{27 \sqrt{2}\left(-1 - i\right)}{2}`), so the number is pulled
from there and `z_display` is only the last-resort fallback.

### Math notation inside Khmer text

Khmer words are rendered by the browser; math is wrapped in `$…$` or `\(…\)`
and rendered by KaTeX. **Never put Khmer inside `\text{...}`** — KaTeX has no
Khmer glyphs and will render tofu. Keep the two in separate spans of the string,
as every branch of `formatLocalizedPrompt` does.

## The server

`lang` travels: `problems.py` → `services.py` → `explainer.py` / `llm.py`.

### LLM prose

`narrate()`, `check_work()` and `check_rubric_feedback()` each carry a Khmer
variant of their prompt instructing authentic Cambodian Grade 12 phrasing
(`គេមាន`, `គេបាន`, `នាំឱ្យ`, `ដូចនេះ`), no English words, and all math wrapped in
`$…$`. The fallback chain is unchanged — Gemini → Ollama → deterministic text.

`check_rubric_feedback()` is the odd one out: its *reference* is always the
Khmer official BAC II key (`correct_solution_km`, which today only the
`functions` topic produces), but its *output* follows `lang`. An English-mode
student gets English commentary grounded in the Khmer key.

### Explanation cache

Redis keys include the language:

```
explain:{topic}:{question_type}:{spec}:{lang}:{steps_digest}
```

Without the `lang` segment an English narration would be served to a Khmer
student, or vice versa, for the rest of the TTL. If you add another prose-
producing cached endpoint, key it the same way.

### Deterministic explanations (`engine/explainer.py`)

`build_text(..., lang="km")` renders the SymPy step list in Khmer. This is the
baseline that shows when both Gemini and Ollama are unavailable — but it is also
the text fed *into* the LLM, so its quality sets a ceiling on the narration.
That second role is easy to forget and is the reason the details below matter.

**Problem line.** `_problem_desc_km()` mirrors `_problem_desc()` topic for
topic. Both route complex numbers through `_complex_given()`, a single reader
that knows every complex template's parameter shape. That shared reader exists
because each template stores something different — `a`/`b`, or `a1/b1/a2/b2`,
or polar `r/k/d/n` — and reading `params["a"]` unconditionally raised
`KeyError` on four of the nine types, taking down `_steps_text()` (and with it
the grade endpoint) in *both* languages.

**Step titles.** Each step resolves through this chain, and the order is the
whole point:

```
step["title_km"]              # a solver that already speaks Khmer
  → _step_title_km(title)     # the step's own specific wording
  → formula name_km           # the broad technique behind the step
  → step["title"]             # English, last resort
```

The formula tag sits *third*, not second, because several topics tag every step
of a solution with one coarse tag. Consulting it first collapsed "Set up the
derivative / Apply the technique / Result" into the same heading repeated three
times — losing information the English path keeps, and feeding the LLM a worse
prompt than English mode gets.

`_step_title_km()` handles the three shapes real titles take:

* a fixed phrase — looked up in `_STEP_TITLE_KM`, **102 base phrases** keyed
  lowercase, with wording drawn from each topic's `data/formulas.json`
  `name_km` so step titles and the formula sheet name a technique identically;
* a part-prefixed phrase (`Part 2.a: Differentiate`) — the prefix is peeled off,
  translated to `ផ្នែក 2.a៖`, and the remainder looked up normally, which keeps
  the ~80 function-study and ~39 probability titles out of the flat table;
* a phrase carrying a rendered expression (`Antiderivative of 5 x`,
  `Take the modulus^(1/3) and divide the angle by 3`) — matched by one of **5
  regex rules**, tried only after the flat table misses so a literal entry
  always wins.

Returning `None` for an unknown title (rather than the English string) is what
lets the caller fall through to the formula name.

### Formula names

Each topic's `engine/topics/<topic>/data/formulas.json` carries `name_km`
alongside `name_en`; `engine/formulas.py` merges those over the built-in
registry. `resolve_formula()` never returns `None` — unknown tags get a fallback
entry — so `.get("name_km")` is always safe. A missing translation comes back
falsy either way (`""` for a JSON entry without one, `None` for a built-in that
was never overlaid), so it falls through to the next link in the chain instead
of rendering an empty heading.

## What is deliberately not translated

* **Step `detail` bodies** in the deterministic explanation. These are SymPy
  LaTeX plus curated technique prose. The LLM rewrites them in Khmer on the
  normal path; they only surface in English if both providers are down.
  Translating them is a content task on the curated exam data, not a code change.
* **The `/admin` page.** Internal tooling, single admin account.
* **The debug panel** on the practice page. Developer-facing.
* **The language switcher's own labels.** Each button names its language *in*
  that language (`ខ្មែរ`, `EN`) — that is the convention, not an oversight.

## Adding to it

**A new interface string.** Add the key to the `Translations` interface, then to
both `en` and `km`. `tsc` fails if you miss one. Use `t("key")` at the call
site, including in `title=` and `aria-label=` attributes — tooltips and
screen-reader labels are interface text too.

**A new topic or question type.** Follow `adding-question-types.md` and
`engine-layout.md` as usual, then:

1. add `name_km` to the topic's `data/formulas.json` entries;
2. add a `QUESTION_TYPE_LABELS` entry per question type (or per
   `question_type:variant`, if the topic has a variant axis);
3. add a branch to `formatLocalizedPrompt()` — or rely on the default, which
   returns the English statement unchanged, which is an acceptable degradation
   but not a good one;
4. add a `_problem_desc` / `_problem_desc_km` branch so the problem line does
   not fall through to dumping the raw `params` dict;
5. add the solver's new step titles to `_STEP_TITLE_KM`.

Step 5 is the one that silently rots, because a missing title degrades quietly
to English instead of failing.

## Checking it still works

There is no test suite in this repo, so these are the sweeps worth re-running
by hand after touching any of the above. Each one is a single script over the
real generators — no fixtures, so they cannot go stale.

| Invariant | How to check |
|---|---|
| Dictionaries in parity | `tsc --noEmit` (the `Translations` interface enforces it) |
| Khmer statements lose no data | Generate questions across every type; assert every integer in `prompt` appears in the localized output |
| No step title falls back to English | Render `build_text(..., lang="km")` across topics × seeds × difficulties; assert every `ជំហានទី` line contains Khmer script |
| No title collapse | Assert `len(set(khmer_titles)) >= len(set(english_titles))` per solution |
| No raw `params` dumps | Assert the problem line contains no `{'` |
| Nothing raises | Build both languages for every topic × question type |

At the time of writing these pass at: 186/186 keys, 972 explanations built
across 10 topics with 0 failures, 0 untranslated titles and 0 collapsed
solutions, and 36 generated questions localized with 0 dropped numbers.
