"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import MathText from "@/components/MathText";
import { api, FormulaCatalog } from "@/lib/api";

export default function FormulasPage() {
  const [catalog, setCatalog] = useState<FormulaCatalog | null>(null);
  const [topicFilter, setTopicFilter] = useState("all");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setCatalog(await api.formulas());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setBusy(false);
      }
    })();
  }, []);

  const topics = ["all", ...(catalog?.topics ?? []).map((t) => t.topic)];
  const visibleTopics = (catalog?.topics ?? []).filter(
    (t) => topicFilter === "all" || t.topic === topicFilter
  );

  return (
    <AuthGuard>
      <div className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Formula sheet</h1>
        <p className="text-sm text-slate-500 mb-6">
          Every technique used across the practice topics — the rule, and the specific formulas
          under it.
        </p>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {busy ? (
          <p className="text-slate-500">Loading...</p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2 mb-6">
              {topics.map((tp) => (
                <button
                  key={tp}
                  onClick={() => setTopicFilter(tp)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium ${
                    topicFilter === tp
                      ? "bg-slate-900 text-white"
                      : "bg-white border border-slate-300 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {tp === "all" ? "All topics" : tp.replace("_", " ")}
                </button>
              ))}
            </div>

            {visibleTopics.map((topic) => (
              <section key={topic.topic} className="mb-8">
                <h2 className="text-lg font-semibold text-slate-900 capitalize mb-3">
                  {topic.topic.replace("_", " ")}
                </h2>
                <div className="space-y-3">
                  {topic.entries.map((e) => (
                    <div key={e.id} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                      <div className="flex flex-wrap items-center gap-2 text-sm">
                        <span className="font-semibold text-slate-900">{e.name_en ?? e.id.replace(/_/g, " ")}</span>
                        {e.name_km && <span className="text-slate-500">{e.name_km}</span>}
                        {e.weight > 0 && (
                          <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-xs">
                            weight {e.weight}
                          </span>
                        )}
                        {e.variants.length > 0 && (
                          <Link
                            href={`/practice?formula=${e.id}`}
                            className="ml-auto px-2.5 py-1 rounded-md bg-slate-900 text-white text-xs font-medium hover:bg-slate-700"
                          >
                            Practice
                          </Link>
                        )}
                      </div>
                      {e.latex && (
                        <div className="mt-2 text-slate-700 overflow-x-auto">
                          <MathText text={`\\(${e.latex}\\)`} />
                        </div>
                      )}
                      {e.formulas.length > 0 && (
                        <ul className="mt-2 space-y-1 text-sm text-slate-600">
                          {e.formulas.map((f, i) => (
                            <li key={i} className="overflow-x-auto">
                              <MathText text={`\\(${f}\\)`} />
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </>
        )}
      </div>
    </AuthGuard>
  );
}
