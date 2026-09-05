"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import { api, Stats } from "@/lib/api";

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.stats();
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setBusy(false);
      }
    })();
  }, []);

  const pct = (v: number) => `${Math.round(v * 100)}%`;

  return (
    <AuthGuard>
      <div className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-6">Stats</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {busy ? (
          <p className="text-slate-500">Loading...</p>
        ) : !stats ? (
          <p className="text-slate-500">Nothing yet.</p>
        ) : (
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="bg-white border border-slate-200 rounded-lg p-5 text-center">
                <div className="text-3xl font-bold text-slate-900">{stats.total_attempts}</div>
                <div className="text-sm text-slate-500">Attempts</div>
              </div>
              <div className="bg-white border border-slate-200 rounded-lg p-5 text-center">
                <div className="text-3xl font-bold text-emerald-600">{stats.correct}</div>
                <div className="text-sm text-slate-500">Correct</div>
              </div>
              <div className="bg-white border border-slate-200 rounded-lg p-5 text-center">
                <div className="text-3xl font-bold text-slate-900">{pct(stats.accuracy)}</div>
                <div className="text-sm text-slate-500">Accuracy</div>
              </div>
            </div>

            {stats.by_topic.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-left text-slate-500">
                    <tr>
                      <th className="px-4 py-2">Question type</th>
                      <th className="px-4 py-2">Attempts</th>
                      <th className="px-4 py-2">Correct</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.by_topic.map((t) => (
                      <tr key={t.question_type} className="border-t border-slate-100">
                        <td className="px-4 py-2 capitalize">{t.question_type.replace("_", " ")}</td>
                        <td className="px-4 py-2">{t.attempts}</td>
                        <td className="px-4 py-2">{t.correct}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {stats.by_formula && stats.by_formula.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="px-4 py-2 font-semibold text-slate-900 text-sm">Formulas to review</div>
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-left text-slate-500">
                    <tr>
                      <th className="px-4 py-2">Formula</th>
                      <th className="px-4 py-2">Steps checked</th>
                      <th className="px-4 py-2">Got it</th>
                      <th className="px-4 py-2">Missed</th>
                      <th className="px-4 py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {stats.by_formula.map((f) => (
                      <tr key={f.formula} className="border-t border-slate-100">
                        <td className="px-4 py-2 capitalize">{f.name_en ?? f.formula.replace("_", " ")}</td>
                        <td className="px-4 py-2">{f.attempts}</td>
                        <td className="px-4 py-2 text-emerald-600">{f.reached}</td>
                        <td className="px-4 py-2 text-red-600">{f.missed}</td>
                        <td className="px-4 py-2 text-right">
                          <Link
                            href={`/practice?formula=${f.formula}`}
                            className="px-2.5 py-1 rounded-md bg-slate-900 text-white text-xs font-medium hover:bg-slate-700"
                          >
                            Practice
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
