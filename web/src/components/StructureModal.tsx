"use client";

import { useState } from "react";

import FunctionGraph from "@/components/FunctionGraph";
import MathText from "@/components/MathText";

// Backend question_km strings use $...$ math markers; KaTeX only recognises
// \(...\) / $$...$$ — normalise to \( \).
function kmMath(s: string): string {
  return s.replace(/\$(.+?)\$/g, "\\($1\\)");
}

type Part = {
  label: string;
  want?: string;
  answer_kind?: string;
  question_km?: string;
  question_en?: string;
  technique?: string;
  technique_en?: string;
  answer?: string;
  answer_latex?: string;
  answer_display?: string;
  answer_display_en?: string;
  variation_table?: {
    columns: string[];
    derivative_sign: string[];
    arrows: string[];
    func_values: string[];
    extrema: { x: string; type: string; value: string }[];
  } | null;
  sign?: unknown | null;
  monotonicity?: unknown | null;
};

type Structure = {
  id: string;
  pattern?: string | null;
  pattern_latex?: string | null;
  sample_prompt?: string | null;
  sample_prompt_latex?: string | null;
  sample_answer?: string | null;
  sample_answer_latex?: string | null;
  formula_tags?: string[] | null;
  source_labels?: string[] | null;
  graph?: unknown;
  parts?: Part[];
  solution_km?: string | null;
  solution_en?: string | null;
};

function VariationTable({ vt }: { vt: NonNullable<Part["variation_table"]> }) {
  const cols = vt.columns;
  const n = cols.length;
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-xs">
        <tbody>
          <tr>
            <td className="border border-slate-300 px-2 py-1 font-semibold text-slate-500">x</td>
            {cols.map((c, i) => (
              <td key={i} className="border border-slate-300 px-2 py-1 text-center">
                {c}
              </td>
            ))}
          </tr>
          <tr>
            <td className="border border-slate-300 px-2 py-1 font-semibold text-slate-500">g&apos;(x)</td>
            <td className="border border-slate-300 px-2 py-1" />
            {vt.derivative_sign.map((s, i) => (
              <td
                key={i}
                className={`border border-slate-300 px-2 py-1 text-center font-bold ${
                  s === "+" ? "text-emerald-600" : s === "-" ? "text-rose-600" : "text-slate-500"
                }`}
              >
                {s}
              </td>
            ))}
          </tr>
          <tr>
            <td className="border border-slate-300 px-2 py-1 font-semibold text-slate-500">g(x)</td>
            {vt.func_values.map((v, i) => (
              <td key={i} className="border border-slate-300 px-2 py-1 text-center">
                <div>{v}</div>
                {i < n - 1 && vt.arrows[i] && (
                  <div className="text-[10px] text-slate-400">
                    {vt.arrows[i] === "↗" ? "↗" : vt.arrows[i] === "↘" ? "↘" : "–"}
                  </div>
                )}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function PartBlock({ part, lang }: { part: Part; lang: "km" | "en" }) {
  const section = part.label.split(".")[0];
  const question = lang === "km" ? part.question_km : part.question_en ?? part.question_km;
  const technique = lang === "km" ? part.technique : part.technique_en ?? part.technique;
  const answer = lang === "km"
    ? part.answer_display ?? part.answer_latex ?? part.answer
    : part.answer_display_en ?? part.answer_display ?? part.answer_latex ?? part.answer;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex items-baseline gap-2">
        <code className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
          {part.label}
        </code>
        <span className="text-[10px] uppercase tracking-wide text-slate-400">{part.want}</span>
      </div>
      {question && (
        <div className="mt-1 text-sm text-slate-700">
          <MathText text={kmMath(question)} />
        </div>
      )}
      {technique && (
        <div className="mt-1 space-y-1 text-xs leading-relaxed text-slate-600">
          {technique
            .replace("។", "។\n")
            .split("\n")
            .map((ln, i) => ln.trim())
            .filter(Boolean)
            .map((ln, i) => (
              <div key={i}>
                <MathText text={kmMath(ln)} />
              </div>
            ))}
        </div>
      )}
      <div className="mt-1 text-sm font-medium text-slate-900">{answer}</div>
      {part.variation_table && (
        <div className="mt-2">
          <VariationTable vt={part.variation_table} />
        </div>
      )}
      {part.sign != null && typeof part.answer_display === "string" && (
        <div className="mt-1 text-xs text-slate-500">sign study as above</div>
      )}
    </div>
  );
}

function SolutionNarrative({ text }: { text: string }) {
  return (
    <div className="space-y-2 whitespace-pre-line text-sm leading-relaxed text-slate-800">
      {text.split("\n").map((line, i) => {
        const clean = line.replace(/\*\*/g, "");
        if (clean.includes("$")) {
          return (
            <div key={i}>
              <MathText text={kmMath(clean)} />
            </div>
          );
        }
        return <div key={i}>{clean}</div>;
      })}
    </div>
  );
}

export default function StructureModal({
  structure,
  onClose,
}: {
  structure: Structure;
  onClose: () => void;
}) {
  const [lang, setLang] = useState<"km" | "en">("km");
  // Group parts by the exam section (label prefix before the first '.').
  const sections = new Map<string, Part[]>();
  for (const p of structure.parts ?? []) {
    const sec = p.label.split(".")[0];
    if (!sections.has(sec)) sections.set(sec, []);
    sections.get(sec)!.push(p);
  }

  const prompt = lang === "km"
    ? structure.sample_prompt_latex ?? structure.sample_prompt
    : structure.sample_prompt ?? structure.sample_prompt_latex;
  const promptIsLatex = lang === "km"
    ? !!structure.sample_prompt_latex
    : !!structure.sample_prompt;
  const solution = lang === "km"
    ? structure.solution_km
    : structure.solution_en ?? structure.solution_km;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="my-6 w-full max-w-3xl rounded-xl bg-slate-50 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div>
            <code className="text-xs text-slate-500">{structure.id}</code>
            {structure.source_labels?.length ? (
              <div className="text-[11px] text-slate-400">{structure.source_labels.join(", ")}</div>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center rounded-md border border-slate-200 bg-white text-xs">
              <button
                className={`rounded-l-md px-2.5 py-1 ${lang === "km" ? "bg-slate-800 text-white" : "text-slate-500 hover:bg-slate-100"}`}
                onClick={() => setLang("km")}
              >
                ខ្មែរ
              </button>
              <button
                className={`rounded-r-md px-2.5 py-1 ${lang === "en" ? "bg-slate-800 text-white" : "text-slate-500 hover:bg-slate-100"}`}
                onClick={() => setLang("en")}
              >
                EN
              </button>
            </div>
            <button
              className="rounded-md px-3 py-1 text-sm text-slate-500 hover:bg-slate-200"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>

        <div className="max-h-[80vh] overflow-y-auto px-4 py-4 space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Function
            </div>
            <div className="mt-1 text-lg text-slate-900">
              {structure.pattern_latex ? (
                <MathText text={`\\(${structure.pattern_latex}\\)`} />
              ) : (
                <p>{structure.pattern}</p>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Exam prompt
            </div>
            <div className="mt-1 text-sm text-slate-800">
              {promptIsLatex && prompt ? (
                <MathText text={`\\(${prompt}\\)`} />
              ) : (
                <p className="whitespace-pre-line">{prompt}</p>
              )}
            </div>
          </div>

          {structure.graph != null && (
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Reference graph
              </div>
              <div className="mt-2">
                <FunctionGraph graph={structure.graph as never} />
              </div>
            </div>
          )}

          <div className="space-y-3">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Sub-questions &amp; answers ({structure.parts?.length ?? 0})
            </div>
            {[...sections.entries()].map(([sec, parts]) => (
              <div key={sec} className="space-y-2">
                <div className="text-sm font-semibold text-slate-600">Question {sec}</div>
                {parts.map((p) => (
                  <PartBlock key={p.label} part={p} lang={lang} />
                ))}
              </div>
            ))}
          </div>

          {solution ? (
            <div className="space-y-2">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                {lang === "km" ? "ដំណោះស្រាយ (Full solution)" : "Full solution"}
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <SolutionNarrative text={solution} />
              </div>
            </div>
          ) : null}

          {structure.formula_tags?.length ? (
            <div className="flex flex-wrap gap-1">
              {structure.formula_tags.map((t) => (
                <code key={t} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
                  {t}
                </code>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
