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
}: {
  prompt: string;
  promptLatex?: string | null;
  questionType: string;
  difficulty: string;
}) {
  const html = renderMath(promptLatex ?? null, prompt);

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-2 text-xs text-slate-500">
        <span className="px-2 py-0.5 rounded bg-slate-100">{questionType}</span>
        <span className="px-2 py-0.5 rounded bg-slate-100">{difficulty}</span>
      </div>
      {html ? (
        <div className="text-lg text-slate-900 overflow-x-auto" dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <p className="text-lg font-semibold text-slate-900">{prompt}</p>
      )}
    </div>
  );
}
