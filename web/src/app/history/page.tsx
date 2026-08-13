"use client";

import { useEffect, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import { api, Attempt } from "@/lib/api";

export default function HistoryPage() {
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.attempts();
        setAttempts(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setBusy(false);
      }
    })();
  }, []);

  return (
    <AuthGuard>
      <div className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-6">History</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {busy ? (
          <p className="text-slate-500">Loading...</p>
        ) : attempts.length === 0 ? (
          <p className="text-slate-500">No attempts yet — head to Practice.</p>
        ) : (
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-500">
                <tr>
                  <th className="px-4 py-2">Answer</th>
                  <th className="px-4 py-2">Result</th>
                  <th className="px-4 py-2">Reason</th>
                  <th className="px-4 py-2">When</th>
                </tr>
              </thead>
              <tbody>
                {attempts.map((a) => (
                  <tr key={a.id} className="border-t border-slate-100">
                    <td className="px-4 py-2">{a.user_answer}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs ${
                          a.correct ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
                        }`}
                      >
                        {a.correct ? "Correct" : "Wrong"}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-600">{a.reason}</td>
                    <td className="px-4 py-2 text-slate-500">{new Date(a.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
