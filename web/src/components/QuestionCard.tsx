import katex from "katex";
import "katex/dist/katex.min.css";

function renderMath(promptLatex: string | null, prompt: string): string {
  if (!promptLatex) return "";
  try {
    return katex.renderToString(promptLatex, {
      throwOnError: false,
      displayMode: true,
    });
  } catch {
    return "";
  }
}

export default function QuestionCard({
  prompt,
  promptLatex,
  questionType,
  difficulty,
  formulaTags,
  formulaDifficulty,
  parts,
  currentPart,
}: {
  prompt: string;
  promptLatex?: string | null;
  questionType: string;
  difficulty: string;
  formulaTags?: string[];
  formulaDifficulty?: string;
  parts?: string[];
  currentPart?: string | null;
}) {
  const html = renderMath(promptLatex ?? null, prompt);
  const formulaLabel = formulaTags?.length
    ? formulaTags.map((t) => t.replaceAll("_", " ")).join(" · ")
    : null;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2 mb-2 text-xs text-slate-500">
        <span className="px-2 py-0.5 rounded bg-slate-100">{questionType}</span>
        <span className="px-2 py-0.5 rounded bg-slate-100">{difficulty}</span>
        {parts?.length ? (
          <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700">
            Parts:{" "}
            {parts.map((p) => (
              <span key={p} className={p === currentPart ? "font-bold text-emerald-900 underline" : ""}>
                {p}
                {p !== parts[parts.length - 1] ? " · " : ""}
              </span>
            ))}
          </span>
        ) : null}
        {formulaDifficulty && (
          <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800">
            formulas: {formulaDifficulty}
          </span>
        )}
      </div>
      {html ? (
        <div className="text-lg text-slate-900 overflow-x-auto" dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <p className="text-lg font-semibold text-slate-900 whitespace-pre-line">{prompt}</p>
      )}
      {formulaLabel && (
        <p className="mt-2 text-xs text-slate-400">{formulaLabel}</p>
      )}
    </div>
  );
}
