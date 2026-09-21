"use client";

import { useEffect, useState } from "react";
import AdminGuard from "@/components/AdminGuard";
import AdminSandbox from "@/components/AdminSandbox";
import FunctionGraph from "@/components/FunctionGraph";
import MathText from "@/components/MathText";
import StructureModal from "@/components/StructureModal";
import { useLanguage } from "@/context/LanguageContext";
import { api, FormulaCatalog, TemplateStructure, TemplateStructures, TemplateSummary } from "@/lib/api";

type Tab = "overview" | "formulas" | "templates" | "sandbox";
type TopicStructures = NonNullable<TemplateStructures["topics"]>[number];

// Backend question_km strings use $...$ math markers; KaTeX auto-render here
// only recognises \(...\) / $$...$$ — normalise to \( \).
function renderMathFormula(s: string): string {
  if (!s) return "";
  if (s.includes("$") || /[\u1780-\u17FF]/.test(s)) return s;
  return `\\(${s}\\)`;
}

function kmMath(s: string): string {
  if (!s) return "";
  return s.replace(/\$(.+?)\$/g, "\\($1\\)");
}

interface LimitSubtopicDef {
  key: string;
  en: string;
  km: string;
  matches: (subfam: string) => boolean;
}

interface LimitCategoryDef {
  key: string;
  en: string;
  km: string;
  subtopics: LimitSubtopicDef[];
}

const LIMIT_CATEGORIES_CONFIG: LimitCategoryDef[] = [
  {
    key: "rational",
    en: "1. Rational limits",
    km: "១. លីមីតសនិទាន",
    subtopics: [
      { key: "powers", en: "1. Algebraic identities (powers)", km: "១. រូបមន្តស្វ័យគុណ (ការេ គូប ដឺក្រេខ្ពស់)", matches: (s) => s === "powers" },
      { key: "quadratics", en: "2. Quadratic trinomials", km: "២. បំបែកត្រីធាដឺក្រេទីពីរ", matches: (s) => s === "quadratics" },
      { key: "binomial", en: "3. Shifted binomials at 0", km: "៣. ពន្លាតទ្វេធាត្រង់ 0", matches: (s) => s === "binomial" },
    ],
  },
  {
    key: "radical",
    en: "2. Radical limits",
    km: "២. លីមីតរ៉ាឌីកាល់",
    subtopics: [
      { key: "sqrt", en: "1. Square root conjugates", km: "១. កន្សោមឆ្លាស់ឬសការេ", matches: (s) => s === "sqrt" },
      { key: "cbrt", en: "2. Cube root conjugates", km: "២. កន្សោមឆ្លាស់ឬសគូប", matches: (s) => s === "cbrt" },
      { key: "double_and_split", en: "3. Double conjugate & split trick", km: "៣. ឆ្លាស់ពីរជាន់ & ថែមថយតួ", matches: (s) => s === "double_and_split" },
    ],
  },
  {
    key: "trig",
    en: "3. Trigonometric limits",
    km: "៣. លីមីតត្រីកោណមាត្រ",
    subtopics: [
      { key: "sinc_standard", en: "1. Fundamental limit sin(kx)/x at 0", km: "១. លីមីតគ្រឹះ sin(kx)/x ត្រង់ 0", matches: (s) => s === "sinc_standard" },
      { key: "change_var", en: "2. Change of variable at non-zero points", km: "២. ប្តូរអថេរត្រង់ π/2, π/3, π/4, π", matches: (s) => s === "change_var" },
      { key: "half_angle", en: "3. Half-angle & double-angle identities", km: "៣. រូបមន្តកន្លះមុំ និងមុំទ្វេ", matches: (s) => s === "half_angle" || s === "double_angle" || s === "quadratic" },
      { key: "sum_product", en: "4. Sum-to-product (Simpson)", km: "៤. បំប្លែងផលបូកទៅផលគុណ (Simpson)", matches: (s) => s === "sum_product" },
      { key: "radical_trig", en: "5. Radicals mixed with trigonometry", km: "៥. កន្សោមឆ្លាស់ឬសការេចម្រុះត្រីកោណមាត្រ", matches: (s) => s === "radical_trig" },
    ],
  },
  {
    key: "exponential",
    en: "4. Exponential limits",
    km: "៤. លីមីតអិចស្ប៉ូណង់ស្យែល",
    subtopics: [
      { key: "zero", en: "1. Indeterminate form 0/0", km: "១. រាងមិនកំណត់ 0/0", matches: (s) => s === "zero" },
      { key: "trig_combo", en: "2. Mixed with trigonometry", km: "២. រាងចម្រុះត្រីកោណមាត្រ", matches: (s) => s === "trig_combo" },
      { key: "one_inf", en: "3. Indeterminate form 1^∞", km: "៣. រាងមិនកំណត់ 1^អនន្ត", matches: (s) => s === "one_inf" },
      { key: "infinity", en: "4. Limits at infinity & growth dominance", km: "៤. លីមីតនៅអនន្ត និងលំដាប់កំណើន", matches: (s) => s === "infinity" },
    ],
  },
  {
    key: "logarithmic",
    en: "5. Logarithmic limits",
    km: "៥. លីមីតលោការីត",
    subtopics: [
      { key: "zero", en: "1. Indeterminate form 0/0", km: "១. រាងមិនកំណត់ 0/0", matches: (s) => s === "zero" },
      { key: "rational", en: "2. Logarithm of rational function", km: "២. លោការីតនៃកន្សោមសនិទាន", matches: (s) => s === "rational" },
      { key: "growth_zero", en: "3. Growth dominance at 0⁺", km: "៣. លំដាប់កំណើនត្រង់ 0⁺ (x ln x)", matches: (s) => s === "growth_zero" },
      { key: "infinity", en: "4. Limits at infinity & growth dominance", km: "៤. លីមីតនៅអនន្ត និងលំដាប់កំណើន", matches: (s) => s === "infinity" },
    ],
  },
  {
    key: "infinity",
    en: "6. Limits at infinity",
    km: "៦. លីមីតនៅអនន្ត",
    subtopics: [
      { key: "conjugate", en: "1. Conjugate at infinity (∞ - ∞)", km: "១. គុណកន្សោមឆ្លាស់នៅអនន្ត (រាង ∞ - ∞)", matches: (s) => s === "conjugate" },
      { key: "rational", en: "2. Rational function at infinity", km: "២. លីមីតអនុគមន៍សនិទាននៅអនន្ត", matches: (s) => s === "rational" },
    ],
  },
];

export default function AdminPage() {
  const { lang, t } = useLanguage();
  const [tab, setTab] = useState<Tab>("overview");
  const [topicFilter, setTopicFilter] = useState("all");
  const [limitCategoryFilter, setLimitCategoryFilter] = useState<string>("all");
  const [limitSubtopicFilter, setLimitSubtopicFilter] = useState<string>("all");
  const [catalog, setCatalog] = useState<FormulaCatalog | null>(null);
  const [summary, setSummary] = useState<TemplateSummary | null>(null);
  const [structuresByTopic, setStructuresByTopic] = useState<Record<string, TopicStructures>>({});
  const [loadingTopics, setLoadingTopics] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [selected, setSelected] = useState<TemplateStructure | null>(null);

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

  // Load topic structure cards in parallel as soon as the Templates tab is active.
  useEffect(() => {
    if (tab !== "templates" || !summary) return;
    const needed =
      topicFilter === "all"
        ? (summary?.topics ?? []).map((t) => t.topic)
        : [topicFilter];

    needed.forEach((tp) => {
      if (structuresByTopic[tp] || loadingTopics[tp]) return;
      setLoadingTopics((m) => ({ ...m, [tp]: true }));
      api
        .templateStructures(tp)
        .then((res) => {
          const t = res.topics?.[0];
          if (t) setStructuresByTopic((m) => ({ ...m, [tp]: t }));
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : "Failed to load");
        })
        .finally(() => {
          setLoadingTopics((m) => ({ ...m, [tp]: false }));
        });
    });
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

  function renderStructureCard(st: TemplateStructure) {
    return (
      <div
        key={st.id}
        onClick={() => setSelected(st)}
        className="cursor-pointer bg-white border border-slate-200 rounded-lg p-4 shadow-sm transition-shadow hover:shadow-md"
      >
        <div className="flex items-start justify-between gap-2 mb-2">
          <code className="px-1.5 py-0.5 rounded bg-slate-100 text-[11px] text-slate-600">
            {st.id}
          </code>
          {st.source_labels && st.source_labels.length > 0 && (
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
        {st.technique && (
          <p className="mt-2 text-xs text-slate-500 leading-snug">
            {st.technique}
          </p>
        )}
        {(st.sample_prompt_latex || st.sample_prompt) && (
          <div className="mt-2 text-sm text-slate-700 overflow-x-auto">
            {st.sample_prompt_latex ? (
              <MathText text={`\\(${st.sample_prompt_latex}\\)`} />
            ) : (
              <p className="whitespace-pre-line">{st.sample_prompt}</p>
            )}
            {(st.sample_answer_latex || st.sample_answer) && (
              <div className="mt-1 text-slate-600">
                <span className="text-slate-400">Answer:</span>{" "}
                <MathText
                  text={`\\(${st.sample_answer_latex ?? st.sample_answer}\\)`}
                  className="inline"
                />
              </div>
            )}
          </div>
        )}
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
                  {p.technique && !/^[A-Za-z]/.test(p.technique.trim()) && (
                    <div className="mt-0.5 text-[11px] leading-snug text-slate-500">
                      <MathText text={kmMath(p.technique)} />
                    </div>
                  )}
                  <div className="mt-0.5 text-slate-900">
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
        {st.formula_tags && st.formula_tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {st.formula_tags.map((t) => (
              <code key={t} className="px-1.5 py-0.5 rounded bg-slate-100 text-[11px]">
                {t}
              </code>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <AdminGuard>
      <div className="max-w-5xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-6">Admin</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {busy ? (
          <p className="text-slate-500">Loading...</p>
        ) : (
          <>
            <div className="flex items-center gap-2 mb-3">
              {(["overview", "formulas", "templates", "sandbox"] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-2 rounded-md text-sm font-medium ${
                    tab === t ? "bg-slate-900 text-white" : "bg-white border border-slate-300 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {t === "overview" ? "Overview" : t === "formulas" ? "Formulas" : t === "templates" ? "Templates" : "Sandbox"}
                </button>
              ))}
            </div>

            {tab !== "sandbox" && (
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
            )}

            {tab === "sandbox" && <AdminSandbox summary={summary} onExit={() => setTab("overview")} />}

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
                    {topic.entries.map((e) => {
                      const primaryName = lang === "km"
                        ? (e.name_km || e.name_en || e.id.replace(/_/g, " "))
                        : (e.name_en || e.name_km || e.id.replace(/_/g, " "));
                      const secondaryName = lang === "km" ? e.name_en : e.name_km;
                      return (
                        <div key={e.id} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                          <div className="flex flex-wrap items-center gap-2 text-sm">
                            <code className="px-2 py-0.5 rounded bg-slate-100 text-xs">{e.id}</code>
                            <span className="font-semibold text-slate-900">{primaryName}</span>
                            {secondaryName && secondaryName !== primaryName && (
                              <span className="text-slate-500">({secondaryName})</span>
                            )}
                            {e.weight > 0 && (() => {
                              const diff = e.weight <= 1 ? "easy" : e.weight <= 2 ? "medium" : "hard";
                              const style = diff === "easy" ? "bg-emerald-100 text-emerald-800" : diff === "medium" ? "bg-amber-100 text-amber-800" : "bg-rose-100 text-rose-800";
                              return (
                                <span className={`px-2 py-0.5 rounded text-xs ${style}`}>
                                  {t(`formulas_difficulty_${diff}` as const)}
                                </span>
                              );
                            })()}
                          </div>
                        {e.latex && (
                          <div className="mt-2 text-slate-700">
                            <MathText text={renderMathFormula(e.latex)} />
                          </div>
                        )}
                        {e.formulas.length > 0 && (
                          <ul className="mt-2 space-y-1 text-sm text-slate-600">
                            {e.formulas.map((f, i) => (
                              <li key={i} className="leading-relaxed">
                                <MathText text={renderMathFormula(f)} />
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    );
                  })}
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
                    ) : topic === "limit" ? (
                      (() => {
                        const allLimitStructures = loaded.question_types.flatMap((qt) => qt.structures);
                        const selectedCatDef = LIMIT_CATEGORIES_CONFIG.find((c) => c.key === limitCategoryFilter);

                        const getCategoryKey = (st: TemplateStructure) =>
                          st.category || st.id.split(":")[1] || "other";
                        const getSubfamilyKey = (st: TemplateStructure) =>
                          st.subfamily || st.id.split(":")[2] || "";

                        const visibleCategories =
                          limitCategoryFilter === "all"
                            ? LIMIT_CATEGORIES_CONFIG
                            : LIMIT_CATEGORIES_CONFIG.filter((c) => c.key === limitCategoryFilter);

                        return (
                          <div className="space-y-6">
                            {/* Main Categories Filter Bar */}
                            <div className="bg-slate-100/70 p-3.5 rounded-xl border border-slate-200">
                              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                                {lang === "km" ? "ជំពូកលីមីតសំខាន់ៗ" : "Limit Categories"}
                              </div>
                              <div className="flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setLimitCategoryFilter("all");
                                    setLimitSubtopicFilter("all");
                                  }}
                                  className={`px-3 py-1.5 rounded-lg text-xs transition-all flex items-center gap-1.5 ${
                                    limitCategoryFilter === "all"
                                      ? "bg-amber-500 text-white font-medium shadow-sm"
                                      : "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
                                  }`}
                                >
                                  <span>{lang === "km" ? "គ្រប់ជំពូកលីមីត" : "All Limits"}</span>
                                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                                    limitCategoryFilter === "all" ? "bg-amber-600 text-white" : "bg-slate-100 text-slate-600"
                                  }`}>
                                    {allLimitStructures.length}
                                  </span>
                                </button>
                                {LIMIT_CATEGORIES_CONFIG.map((cat) => {
                                  const count = allLimitStructures.filter((s) => getCategoryKey(s) === cat.key).length;
                                  const isActive = limitCategoryFilter === cat.key;
                                  return (
                                    <button
                                      key={cat.key}
                                      type="button"
                                      onClick={() => {
                                        setLimitCategoryFilter(cat.key);
                                        setLimitSubtopicFilter("all");
                                      }}
                                      className={`px-3 py-1.5 rounded-lg text-xs transition-all flex items-center gap-1.5 ${
                                        isActive
                                          ? "bg-amber-500 text-white font-medium shadow-sm"
                                          : "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
                                      }`}
                                    >
                                      <span>{lang === "km" ? cat.km : cat.en}</span>
                                      <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                                        isActive ? "bg-amber-600 text-white" : "bg-slate-100 text-slate-600"
                                      }`}>
                                        {count}
                                      </span>
                                    </button>
                                  );
                                })}
                              </div>

                              {/* Subtopic Filter Bar when Category is selected */}
                              {selectedCatDef && (
                                <div className="mt-3 pt-3 border-t border-slate-200/80">
                                  <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                                    {lang === "km" ? "វិធីសាស្ត្រដោះស្រាយ" : "Techniques / Subtopics"}
                                  </div>
                                  <div className="flex flex-wrap gap-1.5">
                                    <button
                                      type="button"
                                      onClick={() => setLimitSubtopicFilter("all")}
                                      className={`px-2.5 py-1 rounded-md text-xs transition-all flex items-center gap-1.5 ${
                                        limitSubtopicFilter === "all"
                                          ? "bg-slate-800 text-white font-medium shadow-sm"
                                          : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
                                      }`}
                                    >
                                      <span>{lang === "km" ? "ទាំងអស់ក្នុងជំពូកនេះ" : `All ${selectedCatDef.en}`}</span>
                                      <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                                        limitSubtopicFilter === "all" ? "bg-slate-700 text-white" : "bg-slate-100 text-slate-600"
                                      }`}>
                                        {allLimitStructures.filter((s) => getCategoryKey(s) === selectedCatDef.key).length}
                                      </span>
                                    </button>
                                    {selectedCatDef.subtopics.map((sub) => {
                                      const count = allLimitStructures.filter(
                                        (s) => getCategoryKey(s) === selectedCatDef.key && sub.matches(getSubfamilyKey(s))
                                      ).length;
                                      const isActive = limitSubtopicFilter === sub.key;
                                      return (
                                        <button
                                          key={sub.key}
                                          type="button"
                                          onClick={() => setLimitSubtopicFilter(sub.key)}
                                          className={`px-2.5 py-1 rounded-md text-xs transition-all flex items-center gap-1.5 ${
                                            isActive
                                              ? "bg-slate-800 text-white font-medium shadow-sm"
                                              : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
                                          }`}
                                        >
                                          <span>{lang === "km" ? sub.km : sub.en}</span>
                                          <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                                            isActive ? "bg-slate-700 text-white" : "bg-slate-100 text-slate-600"
                                          }`}>
                                            {count}
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}
                            </div>

                            {/* Categorized & Subtopic Structure Cards */}
                            {visibleCategories.map((cat) => {
                              const catStructs = allLimitStructures.filter((s) => getCategoryKey(s) === cat.key);
                              if (catStructs.length === 0) return null;

                              const visibleSubtopics =
                                limitSubtopicFilter === "all"
                                  ? cat.subtopics
                                  : cat.subtopics.filter((s) => s.key === limitSubtopicFilter);

                              return (
                                <div key={cat.key} className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-sm">
                                  <div className="flex items-start justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
                                    <div>
                                      <h3 className="text-base font-semibold text-slate-800">
                                        {lang === "km" ? cat.km : cat.en}
                                      </h3>
                                      <p className="text-xs text-slate-400">
                                        {lang === "km" ? cat.en : cat.km}
                                      </p>
                                    </div>
                                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                                      {catStructs.length} template{catStructs.length === 1 ? "" : "s"}
                                    </span>
                                  </div>

                                  <div className="space-y-6">
                                    {visibleSubtopics.map((sub) => {
                                      const subStructs = catStructs.filter((s) => sub.matches(getSubfamilyKey(s)));
                                      if (subStructs.length === 0) return null;
                                      return (
                                        <div key={sub.key}>
                                          <div className="flex items-center gap-2 mb-3">
                                            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                                            <h4 className="text-sm font-semibold text-slate-700">
                                              {lang === "km" ? sub.km : sub.en}
                                            </h4>
                                            <span className="text-xs text-slate-400 font-medium">
                                              ({subStructs.length})
                                            </span>
                                          </div>
                                          <div className="grid gap-3 md:grid-cols-2">
                                            {subStructs.map(renderStructureCard)}
                                          </div>
                                        </div>
                                      );
                                    })}

                                    {/* Uncategorized fallback for the category */}
                                    {limitSubtopicFilter === "all" && (() => {
                                      const uncategorized = catStructs.filter(
                                        (s) => !cat.subtopics.some((sub) => sub.matches(getSubfamilyKey(s)))
                                      );
                                      if (uncategorized.length === 0) return null;
                                      return (
                                        <div>
                                          <div className="flex items-center gap-2 mb-3">
                                            <span className="w-2 h-2 rounded-full bg-slate-400"></span>
                                            <h4 className="text-sm font-semibold text-slate-700">
                                              {lang === "km" ? "ផ្សេងៗ" : "Other"}
                                            </h4>
                                            <span className="text-xs text-slate-400 font-medium">
                                              ({uncategorized.length})
                                            </span>
                                          </div>
                                          <div className="grid gap-3 md:grid-cols-2">
                                            {uncategorized.map(renderStructureCard)}
                                          </div>
                                        </div>
                                      );
                                    })()}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        );
                      })()
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
                            {qt.structures.map(renderStructureCard)}
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
      {selected && (
        <StructureModal structure={selected} onClose={() => setSelected(null)} />
      )}
    </AdminGuard>
  );
}