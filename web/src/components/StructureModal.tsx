"use client";

import React, { Fragment, useState } from "react";

import FunctionGraph from "@/components/FunctionGraph";
import MathText from "@/components/MathText";
import { api } from "@/lib/api";

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
  sign_table?: {
    cols: string[];
    rows: {
      label: string;
      cols: { val: string }[];
    }[];
  } | null;
  sign?: unknown | null;
  monotonicity?: unknown | null;
};

type KmStep = { khmer: string; latex: string };
type KmPart = {
  label: string;
  steps: KmStep[];
  answer_khmer: string;
  answer_latex: string;
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
  solution_km_json?: { parts: KmPart[] } | null;
  solution_en?: string | null;
};

function SignTable({ st }: { st: NonNullable<Part["sign_table"]> }) {
  const mainRow = st.rows[st.rows.length - 1];
  const roots = st.cols.slice(1, -1);
  const firstBound = st.cols[0];
  const lastBound = st.cols[st.cols.length - 1];

  return (
    <div className="my-3 overflow-x-auto">
      <div className="text-[11px] font-semibold text-slate-600 mb-1.5">តារាងសញ្ញា (Sign Table)</div>
      <div className="inline-block bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
        <table className="border-collapse font-sans text-xs">
          <tbody>
            {/* Top row: x, -∞, -3, 3, +∞ */}
            <tr className="border-b border-slate-900">
              <td className="border-r border-slate-900 px-4 py-2 font-bold italic font-serif text-slate-800 text-center min-w-[70px]">
                x
              </td>
              <td className="px-3 py-2 text-slate-700 text-left font-mono">
                <MathText text={`\\(${firstBound}\\)`} />
              </td>
              {roots.map((r, i) => (
                <Fragment key={i}>
                  <td className="px-6 py-2" />
                  <td className="px-4 py-2 text-center font-mono font-semibold text-slate-900">
                    <MathText text={`\\(${r}\\)`} />
                  </td>
                </Fragment>
              ))}
              <td className="px-6 py-2" />
              <td className="px-3 py-2 text-slate-700 text-right font-mono">
                <MathText text={`\\(${lastBound}\\)`} />
              </td>
            </tr>

            {/* Bottom row: expression, -, 0 (on line), +, || (on line), - */}
            <tr>
              <td className="border-r border-slate-900 px-4 py-3 font-semibold text-slate-900 text-center">
                <MathText text={`\\(${mainRow.label}\\)`} />
              </td>
              <td className="px-1" />
              {mainRow.cols.map((cell, cIdx) => {
                const isRoot = cIdx % 2 === 1;
                const v = cell.val;
                const isUndef = v === "‖" || v === "||";

                if (isRoot) {
                  return (
                    <td key={cIdx} className="relative px-0 py-2 text-center w-8">
                      {isUndef ? (
                        /* Double vertical line */
                        <div className="flex items-center justify-center h-8 gap-[3px]">
                          <div className="w-[1.5px] h-8 bg-slate-900" />
                          <div className="w-[1.5px] h-8 bg-slate-900" />
                        </div>
                      ) : (
                        /* Single line with centered 0 */
                        <div className="relative flex items-center justify-center h-8">
                          <div className="absolute inset-y-0 w-[1.5px] bg-slate-900 -top-2 bottom-0" />
                          <span className="relative z-10 bg-white px-1 font-mono text-xs font-bold text-slate-900">
                            0
                          </span>
                        </div>
                      )}
                    </td>
                  );
                }

                /* Open interval sign */
                return (
                  <td key={cIdx} className="px-8 py-3 text-center text-sm font-bold text-slate-800">
                    {v}
                  </td>
                );
              })}
              <td className="px-1" />
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function VariationTable({ vt }: { vt: NonNullable<Part["variation_table"]> }) {
  const cols = vt.columns;
  const n = cols.length;

  const normVal = (v: string | undefined) => {
    if (!v) return "";
    if (v === "oo" || v === "+oo") return "+\\infty";
    if (v === "-oo") return "-\\infty";
    return v;
  };

  return (
    <div className="my-3 overflow-x-auto">
      <div className="text-[11px] font-semibold text-slate-600 mb-1.5">តារាងអថេរភាព (Variation Table)</div>
      <div className="inline-block bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
        <table className="border-collapse font-sans text-xs min-w-[280px]">
          <tbody>
            {/* Row 1: x */}
            <tr className="border-b border-slate-900">
              <td className="border-r border-slate-900 px-4 py-2 font-bold italic font-serif text-slate-800 text-center min-w-[80px]">
                x
              </td>
              <td className="px-3 py-2 text-left font-mono font-semibold text-slate-900">
                <MathText text={`\\(${normVal(cols[0])}\\)`} />
              </td>
              {cols.slice(1, -1).map((c, i) => (
                <Fragment key={i}>
                  <td className="px-4 py-2 text-center font-mono font-semibold text-slate-900">
                    <MathText text={`\\(${normVal(c)}\\)`} />
                  </td>
                </Fragment>
              ))}
              <td className="px-3 py-2 text-right font-mono font-semibold text-slate-900">
                <MathText text={`\\(${normVal(cols[n - 1])}\\)`} />
              </td>
            </tr>

            {/* Row 2: g'(x) */}
            <tr className="border-b border-slate-900">
              <td className="border-r border-slate-900 px-4 py-2 font-semibold text-slate-900 text-center">
                g&apos;(x)
              </td>
              <td colSpan={Math.max(2, n)} className="px-4 py-2 text-center font-bold text-sm text-slate-800">
                <div className="flex items-center justify-around w-full">
                  {vt.derivative_sign.map((s, i) => (
                    <span key={i} className="text-emerald-700 font-bold">{s || "+"}</span>
                  ))}
                </div>
              </td>
            </tr>

            {/* Row 3: y = g(x) */}
            <tr>
              <td className="border-r border-slate-900 px-4 py-5 font-semibold text-slate-900 text-center whitespace-nowrap">
                y = g(x)
              </td>
              <td colSpan={Math.max(2, n)} className="px-3 py-3">
                <div className="flex items-center justify-between w-full h-16 relative">
                  {/* Left limit / value at bottom */}
                  <span className="self-end pb-1 font-mono font-semibold text-slate-900 text-xs">
                    <MathText text={`\\(${normVal(vt.func_values[0])}\\)`} />
                  </span>

                  {/* Arrow in middle */}
                  <div className="flex-1 flex items-center justify-center px-4">
                    <svg className="w-full h-12" preserveAspectRatio="none" viewBox="0 0 100 40">
                      <defs>
                        <marker id="arrowhead" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                          <polygon points="0 0, 6 3, 0 6" fill="#1e293b" />
                        </marker>
                      </defs>
                      <line
                        x1="10"
                        y1="34"
                        x2="90"
                        y2="6"
                        stroke="#1e293b"
                        strokeWidth="1.5"
                        markerEnd="url(#arrowhead)"
                      />
                    </svg>
                  </div>

                  {/* Right limit / value at top */}
                  <span className="self-start pt-1 font-mono font-semibold text-slate-900 text-xs">
                    <MathText text={`\\(${normVal(vt.func_values[n - 1])}\\)`} />
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

const KM_DIGITS: Record<string, string> = {
  "1": "១",
  "2": "២",
  "3": "៣",
  "4": "៤",
  "5": "៥",
  "6": "៦",
  "7": "៧",
  "8": "៨",
  "9": "៩",
};

function getSectionPrompt(sec: string, promptText: string | null | undefined, parts: Part[]): string {
  const kmSec = KM_DIGITS[sec] ?? sec;
  if (promptText) {
    const lines = promptText.split("\n").map((l) => l.trim()).filter(Boolean);
    const regex = new RegExp(`^(?:${sec}|${kmSec})[.\\s]`, "i");
    const match = lines.find((l) => regex.test(l));
    if (match) return match;
  }
  const questions = parts.map((p) => p.question_km?.trim()).filter(Boolean);
  if (questions.length) {
    return `${kmSec}. ${questions.join(" ")}`;
  }
  return `សំណួរទី ${kmSec}`;
}

function PartBlock({
  part,
  kmPart,
  mode,
  graph,
}: {
  part: Part;
  kmPart?: KmPart | null;
  mode: "ai" | "override";
  graph?: unknown;
}) {
  const question = part.question_km;
  const rawTech = part.technique;
  const kmSteps = mode === "ai" ? kmPart?.steps : null;
  const showRawTech = mode === "override" && !!rawTech;
  const signTable = part.sign_table;
  const variationTable = part.variation_table;
  const isDrawPart = part.want === "draw" || part.answer_kind === "draw";

  const answer = mode === "ai" && kmPart?.answer_khmer
    ? kmPart.answer_khmer
    : part.answer_display ?? part.answer_latex ?? part.answer;

  return (
    <div className="space-y-3 py-2 border-b border-slate-100 last:border-0">
      {question && (
        <div className="flex items-baseline gap-2 text-base font-semibold text-slate-800">
          <span className="text-sky-600 font-bold text-lg">+</span>
          <MathText text={kmMath(question.endsWith("៖") || question.endsWith(":") ? question : `${question} ៖`)} />
        </div>
      )}

      {kmSteps && (
        <div className="pl-4 space-y-2.5 text-[15px] sm:text-base leading-relaxed text-slate-800">
          {kmSteps.map((s, i) => {
            const hasEquation = s.khmer.includes("=") || (!!s.latex && s.khmer.includes(s.latex));
            return (
              <div key={i} className="space-y-1.5">
                <MathText text={kmMath(s.khmer)} />
                {s.latex && !hasEquation && (
                  <div className="py-1 text-slate-900 overflow-x-auto font-medium text-base">
                    <MathText text={`\\[${s.latex}\\]`} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Embed Sign Table right inside Domain part */}
      {signTable && (
        <div className="pl-4 my-2">
          <SignTable st={signTable} />
        </div>
      )}

      {/* Embed Variation Table right inside Variation Table part */}
      {variationTable && (
        <div className="pl-4 my-2">
          <VariationTable vt={variationTable} />
        </div>
      )}

      {/* Embed Graph right inside Draw Graph part */}
      {isDrawPart && graph != null && (
        <div className="pl-4 my-3 max-w-lg">
          <div className="text-xs font-semibold text-slate-600 mb-1.5">ក្រាប C និងបន្ទាត់ប៉ះ T ៖</div>
          <FunctionGraph graph={graph as never} />
        </div>
      )}

      {showRawTech && (
        <div className="pl-4 space-y-1.5 text-[15px] sm:text-base leading-relaxed text-slate-700">
          {rawTech
            .replace("។", "។\n")
            .split("\n")
            .map((ln) => ln.trim())
            .filter(Boolean)
            .map((ln, i) => (
              <div key={i}>
                <MathText text={kmMath(ln)} />
              </div>
            ))}
        </div>
      )}

      {answer && !isDrawPart && (
        <div className="pl-4 pt-1 text-base font-semibold text-slate-900">
          {!answer.startsWith("ដូចនេះ") && !answer.startsWith("ចម្លើយ") ? (
            <span>ចម្លើយ៖ <MathText text={kmMath(answer)} /></span>
          ) : (
            <MathText text={kmMath(answer)} />
          )}
        </div>
      )}
    </div>
  );
}

export default function StructureModal({
  structure: initialStructure,
  onClose,
}: {
  structure: Structure;
  onClose: () => void;
}) {
  const [structure, setStructure] = useState<Structure>(initialStructure);
  const [mode, setMode] = useState<"ai" | "override">("ai");
  const [regenerating, setRegenerating] = useState(false);

  const handleRegenerate = async () => {
    try {
      setRegenerating(true);
      const res = await api.regenerateStructure(structure.id);
      if (res?.structure) {
        setStructure(res.structure as unknown as Structure);
      }
    } catch (err) {
      console.error("Failed to regenerate:", err);
    } finally {
      setRegenerating(false);
    }
  };

  // Group parts by the exam section (label prefix before the first '.').
  const sections = new Map<string, Part[]>();
  for (const p of structure.parts ?? []) {
    const sec = p.label.split(".")[0];
    if (!sections.has(sec)) sections.set(sec, []);
    sections.get(sec)!.push(p);
  }

  const prompt = structure.sample_prompt_latex ?? structure.sample_prompt;
  const promptIsLatex = !!structure.sample_prompt_latex;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="my-6 w-full max-w-4xl rounded-2xl bg-white shadow-2xl border border-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Topbar */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 bg-slate-50/80 rounded-t-2xl">
          <div>
            <div className="flex items-center gap-2">
              <code className="text-xs font-semibold text-slate-700 bg-slate-200 px-2 py-0.5 rounded">
                {structure.id}
              </code>
              {structure.source_labels?.length ? (
                <span className="text-xs text-slate-500 font-medium">{structure.source_labels.join(", ")}</span>
              ) : null}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="flex items-center gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-100 disabled:opacity-50 transition shadow-sm"
              title="Re-run SymPy verification + live Gemini AI narration"
            >
              <span className={regenerating ? "animate-spin" : ""}>🔄</span>
              <span>{regenerating ? "Generating..." : "Generate"}</span>
            </button>
            <div className="flex items-center rounded-lg border border-slate-300 bg-white p-0.5 text-xs shadow-sm">
              <button
                className={`rounded-md px-3 py-1.5 transition ${mode === "ai" ? "bg-slate-800 text-white font-semibold" : "text-slate-600 hover:bg-slate-100"}`}
                onClick={() => setMode("ai")}
              >
                ខ្មែរ (AI)
              </button>
              <button
                className={`rounded-md px-3 py-1.5 transition ${mode === "override" ? "bg-slate-800 text-white font-semibold" : "text-slate-600 hover:bg-slate-100"}`}
                onClick={() => setMode("override")}
              >
                ខ្មែរ (Override)
              </button>
            </div>
            <button
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-500 hover:bg-slate-200 transition"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>

        {/* Modal Scroll Content */}
        <div className="max-h-[82vh] overflow-y-auto overflow-x-hidden px-4 sm:px-6 py-6 space-y-6">
          {/* Exam Header: Function Pattern & Main Statement */}
          <div className="rounded-xl border border-sky-200 bg-sky-50/50 p-5 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-sky-700 mb-1">
              ប្រធានវិញ្ញាសា (Exam Problem)
            </div>
            <div className="text-xl sm:text-2xl font-bold text-slate-900 py-1">
              {structure.pattern_latex ? (
                <MathText text={`\\(${structure.pattern_latex}\\)`} />
              ) : (
                <p>{structure.pattern}</p>
              )}
            </div>
            {prompt && (
              <div className="mt-2 text-base text-slate-800 leading-relaxed">
                {promptIsLatex ? (
                  <MathText text={`\\(${prompt}\\)`} />
                ) : (
                  <p className="whitespace-pre-line">{prompt}</p>
                )}
              </div>
            )}
          </div>

          {/* Unified Step-by-Step Solution Flow */}
          <div className="space-y-6">
            <div className="text-sm font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 pb-2">
              {mode === "ai" ? "ដំណោះស្រាយលម្អិតផ្លូវការ (Official Step-by-Step Solution)" : "ដំណោះស្រាយឯកសារ (File Override Solution)"}
            </div>

            {[...sections.entries()].map(([sec, parts]) => {
              const secHeader = getSectionPrompt(sec, prompt, parts);
              return (
                <div key={sec} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
                  {/* Main Question Heading */}
                  <div className="border-b border-slate-200 pb-3">
                    <h3 className="text-lg sm:text-xl font-bold text-slate-900 leading-snug">
                      <MathText text={kmMath(secHeader)} />
                    </h3>
                  </div>

                  {/* Sub-steps and calculations */}
                  <div className="space-y-3">
                    {parts.map((p) => (
                      <PartBlock
                        key={p.label}
                        part={p}
                        kmPart={structure.solution_km_json?.parts?.find((kp) => kp.label === p.label)}
                        mode={mode}
                        graph={structure.graph}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {structure.formula_tags?.length ? (
            <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-100">
              <span className="text-xs text-slate-400 font-medium">Formula tags:</span>
              {structure.formula_tags.map((t) => (
                <code key={t} className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600 font-mono">
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
