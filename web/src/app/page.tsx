import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-20 text-center">
      <h1 className="text-4xl font-extrabold text-slate-900 sm:text-5xl">
        BACII Math Practice
      </h1>
      <p className="mt-4 text-lg text-slate-600 max-w-2xl mx-auto">
        Generate BAC II math problems (complex numbers for now), write your answer
        by hand, and get instant grading with concise step-by-step explanations.
      </p>
      <div className="mt-8 flex items-center justify-center gap-4">
        <Link
          href="/practice"
          className="px-5 py-2.5 rounded-lg bg-slate-900 text-white font-medium hover:bg-slate-700"
        >
          Start practicing
        </Link>
        <Link
          href="/signup"
          className="px-5 py-2.5 rounded-lg border border-slate-300 text-slate-700 font-medium hover:bg-slate-50"
        >
          Create account
        </Link>
      </div>
      <div className="mt-16 grid gap-6 sm:grid-cols-3">
        <div className="bg-white border border-slate-200 rounded-lg p-6 text-left">
          <h3 className="font-semibold text-slate-900">Write it by hand</h3>
          <p className="mt-2 text-sm text-slate-600">
            Draw your answer on the canvas or upload a photo — no typing needed.
          </p>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-6 text-left">
          <h3 className="font-semibold text-slate-900">Instant grading</h3>
          <p className="mt-2 text-sm text-slate-600">
            SymPy verifies your answer exactly — right or wrong, immediately.
          </p>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-6 text-left">
          <h3 className="font-semibold text-slate-900">Step-by-step help</h3>
          <p className="mt-2 text-sm text-slate-600">
            Get a concise, AI-explained solution for every problem.
          </p>
        </div>
      </div>
    </div>
  );
}
