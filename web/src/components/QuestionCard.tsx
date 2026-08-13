export default function QuestionCard({
  prompt,
  questionType,
  difficulty,
}: {
  prompt: string;
  questionType: string;
  difficulty: string;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-2 text-xs text-slate-500">
        <span className="px-2 py-0.5 rounded bg-slate-100">{questionType}</span>
        <span className="px-2 py-0.5 rounded bg-slate-100">{difficulty}</span>
      </div>
      <p className="text-lg font-semibold text-slate-900">{prompt}</p>
    </div>
  );
}
