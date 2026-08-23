"use client";

import { useEffect, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import MathText from "@/components/MathText";
import { api, FormulaCatalog, TemplateStructures } from "@/lib/api";

type Tab = "formulas" | "templates";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("formulas");
  const [topicFilter, setTopicFilter] = useState("all");
  const [catalog, setCatalog] = useState<FormulaCatalog | null>(null);
  const [inventory, setInventory] = useState<TemplateStructures | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [c, t] = await Promise.all([api.formulas(), api.templateStructures()]);
        setCatalog(c);
        setInventory(t);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setBusy(false);
      }
    })();
  }, []);

  const topics = [
    "all",
    ...new Set([
      ...(catalog?.topics ?? []).map((t) => t.topic),
      ...(inventory?.topics ?? []).map((t) => t.topic),
    ]),
  ];
  const visibleFormulaTopics = (catalog?.topics ?? []).filter(
    (t) => topicFilter === "all" || t.topic === topicFilter
  );
  const visibleTemplateTopics = (inventory?.topics ?? []).filter(
    (t) => topicFilter === "all" || t.topic === topicFilter
  );

  return (
    <AuthGuard>
      <div className="max-w-5xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-6">Admin</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {busy ? (
          <p className="text-slate-500">Loading...</p>
        ) : (
          <>
            <div className="flex items-center gap-2 mb-3">
              {(["formulas", "templates"] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-2 rounded-md text-sm font-medium ${
                    tab === t ? "bg-slate-900 text-white" : "bg-white border border-slate-300 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {t === "formulas" ? "Formulas" : "Templates"}
                </button>
              ))}
            </div>

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

            {tab === "formulas" &&
              visibleFormulaTopics.map((topic) => (
                <section key={topic.topic} className="mb-8">
                  <h2 className="text-lg font-semibold text-slate-900 capitalize mb-3">
                    {topic.topic.replace("_", " ")}
                  </h2>
                  <div className="space-y-3">
                    {topic.entries.map((e) => (
                      <div key={e.id} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                        <div className="flex flex-wrap items-center gap-2 text-sm">
                          <code className="px-2 py-0.5 rounded bg-slate-100 text-xs">{e.id}</code>
                          <span className="font-semibold text-slate-900">{e.name_en}</span>
                          {e.name_km && <span className="text-slate-500">{e.name_km}</span>}
                          <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-xs">
                            weight {e.weight}
                          </span>
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

            {tab === "templates" &&
              visibleTemplateTopics.map((topic) => (
                <section key={topic.topic} className="mb-8">
                  <h2 className="text-lg font-semibold text-slate-900 capitalize mb-3">
                    {topic.topic.replace("_", " ")}
                  </h2>
                  {topic.question_types.map((qt) => (
                    <div key={qt.question_type} className="mb-6">
                      <h3 className="text-sm font-medium text-slate-600 capitalize mb-2">
                        {qt.question_type.replace("_", " ")}
                        <span className="ml-2 text-xs text-slate-400">
                          {qt.structures.length} structure{qt.structures.length === 1 ? "" : "s"}
                        </span>
                      </h3>
                      <div className="grid gap-3 md:grid-cols-2">
                        {qt.structures.map((st) => (
                          <div key={st.id} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                            <div className="flex items-start justify-between gap-2 mb-2">
                              <code className="px-1.5 py-0.5 rounded bg-slate-100 text-[11px] text-slate-600">
                                {st.id}
                              </code>
                              {st.source_labels.length > 0 && (
                                <span className="text-[11px] text-slate-400">
                                  {st.source_labels.join(", ")}
                                </span>
                              )}
                            </div>
                            <div className="text-sm text-slate-800 overflow-x-auto bg-slate-50 rounded p-2">
                              {st.pattern_latex ? (
                                <MathText text={`\\(${st.pattern_latex}\\)`} />
                              ) : (
                                <p>{st.pattern}</p>
                              )}
                            </div>
                            <div className="mt-2 text-sm text-slate-700 overflow-x-auto">
                              {st.sample_prompt_latex ? (
                                <MathText text={`\\(${st.sample_prompt_latex}\\)`} />
                              ) : (
                                <p className="whitespace-pre-line">{st.sample_prompt}</p>
                              )}
                              <div className="mt-1 text-slate-600">
                                <span className="text-slate-400">Answer:</span>{" "}
                                <MathText
                                  text={`\\(${st.sample_answer_latex ?? st.sample_answer}\\)`}
                                  className="inline"
                                />
                              </div>
                            </div>
                            {st.formula_tags.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1">
                                {st.formula_tags.map((t) => (
                                  <code key={t} className="px-1.5 py-0.5 rounded bg-slate-100 text-[11px]">
                                    {t}
                                  </code>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </section>
              ))}
          </>
        )}
      </div>
    </AuthGuard>
  );
}