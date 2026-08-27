"use client";

import { useEffect, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import FunctionGraph from "@/components/FunctionGraph";
import MathText from "@/components/MathText";
import { api, FormulaCatalog, TemplateStructures, TemplateSummary } from "@/lib/api";

type Tab = "overview" | "formulas" | "templates";
type TopicStructures = NonNullable<TemplateStructures["topics"]>[number];

// Backend question_km strings use $...$ math markers; KaTeX auto-render here
// only recognises \(...\) / $$...$$ — normalise to \( \).
function kmMath(s: string): string {
  return s.replace(/\$(.+?)\$/g, "\\($1\\)");
}

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("overview");
  const [topicFilter, setTopicFilter] = useState("all");
  const [catalog, setCatalog] = useState<FormulaCatalog | null>(null);
  const [summary, setSummary] = useState<TemplateSummary | null>(null);
  const [structuresByTopic, setStructuresByTopic] = useState<Record<string, TopicStructures>>({});
  const [loadingTopics, setLoadingTopics] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  // Overview + topic pills need only the cheap summary; full structure cards
  // are fetched lazily per topic (see the effect below) so the first paint
  // doesn't pay for every topic's SymPy solving at once.
  useEffect(() => {
    (async () => {
      try {
        const [c, s] = await Promise.all([api.formulas(), api.templateSummary()]);
        setCatalog(c);
        setSummary(s);
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
      ...(summary?.topics ?? []).map((t) => t.topic),
    ]),
  ];
  const visibleFormulaTopics = (catalog?.topics ?? []).filter(
    (t) => topicFilter === "all" || t.topic === topicFilter
  );
  const visibleTemplateTopics =
    topicFilter === "all"
      ? (summary?.topics ?? []).map((t) => t.topic)
      : [topicFilter];

  // Lazy-load a topic's structure cards only when the Templates tab needs it.
  // "All topics" loads them one at a time so cards stream in bit by bit
  // instead of blocking the page on the slowest topic (integrals ~26s first
  // time). Loaded topics are cached so revisits are instant.
  useEffect(() => {
    if (tab !== "templates") return;
    const needed =
      topicFilter === "all"
        ? (summary?.topics ?? []).map((t) => t.topic)
        : [topicFilter];
    (async () => {
      for (const tp of needed) {
        if (structuresByTopic[tp] || loadingTopics[tp]) continue;
        setLoadingTopics((m) => ({ ...m, [tp]: true }));
        try {
          const res = await api.templateStructures(tp);
          const t = res.topics[0];
          if (t) setStructuresByTopic((m) => ({ ...m, [tp]: t }));
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to load");
        } finally {
          setLoadingTopics((m) => ({ ...m, [tp]: false }));
        }
      }
    })();
  }, [tab, topicFilter, summary, structuresByTopic, loadingTopics]);

  // Per-topic rollup for the Overview dashboard: how many question types and
  // exercise-level structures (a limit technique, an integral variant, a
  // probability scenario, ...) each topic actually has right now, plus which
  // difficulties and how many are backed by a real curated BAC II exercise
  // (curated > 0) vs. purely procedural.
  const topicOverview = (summary?.topics ?? []).map((t) => ({
    topic: t.topic,
    questionTypes: t.question_types,
    structureCount: t.structure_count,
    difficulties: t.difficulties,
    curated: t.curated,
    formulaCount: catalog?.topics.find((c) => c.topic === t.topic)?.entries.length ?? 0,
  }));

  const visibleOverviewTopics = topicOverview.filter(
    (t) => topicFilter === "all" || t.topic === topicFilter
  );

  const totals = {
    topics: topicOverview.length,
    questionTypes: topicOverview.reduce((n, t) => n + t.questionTypes.length, 0),
    structures: topicOverview.reduce((n, t) => n + t.structureCount, 0),
    formulas: (catalog?.topics ?? []).reduce((n, t) => n + t.entries.length, 0),
  };

  const DIFFICULTY_ORDER = ["easy", "medium", "hard"];

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
              {(["overview", "formulas", "templates"] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-2 rounded-md text-sm font-medium ${
                    tab === t ? "bg-slate-900 text-white" : "bg-white border border-slate-300 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {t === "overview" ? "Overview" : t === "formulas" ? "Formulas" : "Templates"}
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

            {tab === "overview" && (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
                  {[
                    { label: "Topics", value: totals.topics },
                    { label: "Question types", value: totals.questionTypes },
                    { label: "Exercise types", value: totals.structures },
                    { label: "Formulas", value: totals.formulas },
                  ].map((card) => (
                    <div key={card.label} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                      <div className="text-2xl font-bold text-slate-900">{card.value}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{card.label}</div>
                    </div>
                  ))}
                </div>

                <div className="space-y-4">
                  {visibleOverviewTopics.map((t) => (
                    <section key={t.topic} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
                        <h2 className="text-lg font-semibold text-slate-900 capitalize">
                          {t.topic.replace("_", " ")}
                        </h2>
                        <div className="flex flex-wrap items-center gap-1.5 text-xs">
                          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                            {t.questionTypes.length} question type{t.questionTypes.length === 1 ? "" : "s"}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                            {t.structureCount} exercise type{t.structureCount === 1 ? "" : "s"}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                            {t.formulaCount} formula{t.formulaCount === 1 ? "" : "s"}
                          </span>
                          {t.curated > 0 && (
                            <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                              {t.curated} curated (real BAC II)
                            </span>
                          )}
                          {DIFFICULTY_ORDER.filter((d) => t.difficulties.includes(d)).map((d) => (
                            <span key={d} className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 capitalize">
                              {d}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {t.questionTypes.map((qt) => (
                          <span
                            key={qt.question_type}
                            className="px-2.5 py-1 rounded-full border border-slate-200 text-xs text-slate-700"
                          >
                            {qt.question_type.replace("_", " ")}
                            <span className="ml-1.5 text-slate-400">{qt.count}</span>
                          </span>
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              </>
            )}

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
              visibleTemplateTopics.map((topic) => {
                const loaded = structuresByTopic[topic];
                return (
                  <section key={topic} className="mb-8">
                    <h2 className="text-lg font-semibold text-slate-900 capitalize mb-3">
                      {topic.replace("_", " ")}
                    </h2>
                    {!loaded ? (
                      <p className="text-sm text-slate-500">
                        {loadingTopics[topic]
                          ? `Loading ${topic.replace("_", " ")} structures…`
                          : `Not loaded — switch to this topic to load it.`}
                      </p>
                    ) : (
                      loaded.question_types.map((qt) => (
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
                                {st.parts && st.parts.length > 0 && (
                                  <div className="mt-3 border-t border-slate-200 pt-2 space-y-2">
                                    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
                                      Parts & answers
                                    </div>
                                    {st.parts.map((p) => (
                                      <div key={p.label} className="flex items-start gap-2 text-xs">
                                        <code className="shrink-0 mt-0.5 px-1 py-0.5 rounded bg-slate-100 text-[11px] text-slate-600">
                                          {p.label}
                                        </code>
                                        <div className="min-w-0 flex-1 text-slate-700">
                                          <MathText text={kmMath(p.question_km ?? p.want ?? "")} />
                                          <div className="text-slate-500">
                                            → <span>{p.answer_display ?? p.answer}</span>
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                                {st.graph && (
                                  <details className="mt-3 border-t border-slate-200 pt-2">
                                    <summary className="cursor-pointer text-xs font-medium text-slate-600 hover:text-slate-900 select-none">
                                      Show graph ▾
                                    </summary>
                                    <div className="mt-2">
                                      <FunctionGraph graph={st.graph} />
                                    </div>
                                  </details>
                                )}
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
                      ))
                    )}
                  </section>
                );
              })}
          </>
        )}
      </div>
    </AuthGuard>
  );
}