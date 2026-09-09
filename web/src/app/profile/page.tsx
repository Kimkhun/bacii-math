"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import MathText from "@/components/MathText";
import { api, FormulaSkill, Profile, Skill, Suggestion, TopicProgress } from "@/lib/api";

// One colour scale for every bar on the page, so a 40 always looks like a 40
// whether it's the headline, a topic, or a single technique.
function levelColor(level: number) {
  if (level >= 75) return { bar: "bg-emerald-500", text: "text-emerald-700", soft: "bg-emerald-50" };
  if (level >= 55) return { bar: "bg-sky-500", text: "text-sky-700", soft: "bg-sky-50" };
  if (level >= 30) return { bar: "bg-amber-500", text: "text-amber-700", soft: "bg-amber-50" };
  return { bar: "bg-red-500", text: "text-red-700", soft: "bg-red-50" };
}

const STATUS_LABEL: Record<Skill["status"], string> = {
  untouched: "Not tried",
  learning: "Learning",
  shaky: "Shaky",
  solid: "Solid",
  mastered: "Mastered",
};

const SUGGESTION_STYLE: Record<Suggestion["kind"], { label: string; className: string }> = {
  weak_skill: { label: "Weak spot", className: "bg-red-100 text-red-700 border-red-200" },
  weak_formula: { label: "Missing step", className: "bg-orange-100 text-orange-700 border-orange-200" },
  rusty_skill: { label: "Getting rusty", className: "bg-amber-100 text-amber-700 border-amber-200" },
  unproven_skill: { label: "Almost there", className: "bg-sky-100 text-sky-700 border-sky-200" },
  new_skill: { label: "Not tried yet", className: "bg-slate-100 text-slate-600 border-slate-200" },
  new_topic: { label: "Next topic", className: "bg-violet-100 text-violet-700 border-violet-200" },
  first_steps: { label: "Start here", className: "bg-emerald-100 text-emerald-700 border-emerald-200" },
};

function Bar({ level, className = "" }: { level: number; className?: string }) {
  const { bar } = levelColor(level);
  return (
    <div className={`h-2 w-full rounded-full bg-slate-100 overflow-hidden ${className}`}>
      <div
        className={`h-full rounded-full ${bar} transition-[width] duration-500`}
        style={{ width: `${Math.max(level > 0 ? 2 : 0, Math.min(100, level))}%` }}
      />
    </div>
  );
}

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

/** Last 14 days, gaps filled, as a small accuracy strip. */
function ActivityStrip({ activity }: { activity: Profile["activity"] }) {
  const days = useMemo(() => {
    const byDate = new Map(activity.map((a) => [a.date, a]));
    const out: { date: string; attempts: number; correct: number }[] = [];
    // Keys are UTC dates, because that's what Postgres groups the attempts by
    // — mixing in local date arithmetic would shift the buckets by a day.
    const today = new Date();
    for (let i = 13; i >= 0; i--) {
      const d = new Date(
        Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() - i)
      );
      const key = d.toISOString().slice(0, 10);
      out.push(byDate.get(key) ?? { date: key, attempts: 0, correct: 0 });
    }
    return out;
  }, [activity]);
  const max = Math.max(1, ...days.map((d) => d.attempts));

  return (
    <div>
      {/* items-stretch, not items-end: the day columns size the percentage-height
          bars inside them, and a percentage resolves to 0 against an auto height. */}
      <div className="flex items-stretch gap-1 h-12">
        {days.map((d) => (
          <div
            key={d.date}
            title={`${d.date}: ${d.correct}/${d.attempts} right`}
            className="flex-1 flex flex-col justify-end gap-px"
          >
            {d.attempts > 0 ? (
              <>
                <div
                  className="w-full rounded-t-sm bg-slate-200"
                  style={{ height: `${((d.attempts - d.correct) / max) * 100}%` }}
                />
                <div
                  className="w-full rounded-b-sm bg-emerald-500"
                  style={{ height: `${(d.correct / max) * 100}%` }}
                />
              </>
            ) : (
              <div className="w-full h-1 rounded-sm bg-slate-100" />
            )}
          </div>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-slate-400">
        <span>14 days ago</span>
        <span>Today</span>
      </div>
    </div>
  );
}

function SuggestionCard({ s }: { s: Suggestion }) {
  const style = SUGGESTION_STYLE[s.kind] ?? SUGGESTION_STYLE.new_skill;
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${style.className}`}>
          {style.label}
        </span>
        {s.topic_label && <span className="text-[11px] text-slate-400">{s.topic_label}</span>}
      </div>
      <h3 className="font-semibold text-slate-900 text-sm">{s.title}</h3>
      <p className="text-sm text-slate-600">{s.reason}</p>
      {s.contrast && <p className="text-sm text-slate-500 italic">{s.contrast}</p>}
      {s.detail && <p className="text-sm text-slate-500">{s.detail}</p>}
      {s.skill_key && (
        <Link
          href={`/practice?skill=${encodeURIComponent(s.skill_key)}`}
          className="mt-1 self-start px-3 py-1.5 rounded-md bg-slate-900 text-white text-xs font-medium hover:bg-slate-700"
        >
          Practise this
        </Link>
      )}
    </div>
  );
}

function SkillRow({ s }: { s: Skill }) {
  const { text } = levelColor(s.level);
  const untouched = s.evidence <= 0;
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 border-t border-slate-100">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-sm truncate ${untouched ? "text-slate-400" : "text-slate-900"}`}>
            {s.label}
          </span>
          <span className="text-[11px] text-slate-400 capitalize shrink-0">{s.difficulty}</span>
        </div>
        <Bar level={s.level} className="mt-1.5" />
      </div>
      <div className="w-24 text-right text-xs text-slate-500 shrink-0">
        {untouched ? "—" : `${s.correct}/${s.attempts} right`}
      </div>
      <div className={`w-16 text-right text-sm font-semibold shrink-0 ${untouched ? "text-slate-300" : text}`}>
        {untouched ? "–" : Math.round(s.level)}
      </div>
      <div className="w-20 text-right text-[11px] text-slate-400 shrink-0">{STATUS_LABEL[s.status]}</div>
      <Link
        href={`/practice?skill=${encodeURIComponent(s.key)}`}
        className="shrink-0 px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-xs font-medium hover:bg-slate-200"
      >
        Practise
      </Link>
    </div>
  );
}

function TopicCard({
  topic,
  skills,
  open,
  onToggle,
}: {
  topic: TopicProgress;
  skills: Skill[];
  open: boolean;
  onToggle: () => void;
}) {
  const { text } = levelColor(topic.score);
  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
      <button onClick={onToggle} className="w-full text-left px-4 py-3 hover:bg-slate-50">
        <div className="flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 text-sm">{topic.label}</span>
              {!topic.practice && (
                <span className="text-[11px] text-slate-400">(not counted in your level)</span>
              )}
            </div>
            <Bar level={topic.score} className="mt-2" />
            <div className="mt-1.5 text-xs text-slate-500">
              {topic.engaged
                ? `${topic.skills_practised} of ${topic.skills_total} exercise types practised · ${topic.correct}/${topic.attempts} right · ${pct(topic.coverage)} of the topic proven`
                : `Not started — ${topic.skills_total} exercise types waiting`}
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className={`text-2xl font-bold ${topic.engaged ? text : "text-slate-300"}`}>
              {topic.engaged ? Math.round(topic.score) : "–"}
            </div>
            <div className="text-[11px] text-slate-400">{topic.engaged ? topic.band : "—"}</div>
          </div>
          <span className="text-slate-400 text-xs shrink-0">{open ? "▲" : "▼"}</span>
        </div>
      </button>
      {open && (
        <div>
          {skills.map((s) => (
            <SkillRow key={s.key} s={s} />
          ))}
        </div>
      )}
    </div>
  );
}

function FormulaTable({ formulas }: { formulas: FormulaSkill[] }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-100">
        <h2 className="font-semibold text-slate-900 text-sm">Steps you keep missing</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Individual formulas the step-checker watched in your written work — finer than an exercise type.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm min-w-[560px]">
          <thead className="bg-slate-50 text-left text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Formula</th>
              <th className="px-4 py-2 font-medium">Reached</th>
              <th className="px-4 py-2 font-medium">Level</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {formulas.map((f) => {
              const { text } = levelColor(f.level);
              return (
                <tr key={f.formula} className="border-t border-slate-100 align-top">
                  <td className="px-4 py-2">
                    <div className="text-slate-900">{f.name}</div>
                    {f.latex && (
                      <div className="text-xs text-slate-500 mt-0.5 overflow-x-auto">
                        <MathText text={`\\(${f.latex}\\)`} />
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-2 text-slate-600 whitespace-nowrap">
                    {f.correct}/{f.attempts}
                  </td>
                  <td className={`px-4 py-2 font-semibold ${text}`}>{Math.round(f.level)}</td>
                  <td className="px-4 py-2 text-right">
                    {f.skill_key && (
                      <Link
                        href={`/practice?skill=${encodeURIComponent(f.skill_key)}`}
                        className="px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-xs font-medium hover:bg-slate-200 whitespace-nowrap"
                      >
                        Practise
                      </Link>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [openTopics, setOpenTopics] = useState<Record<string, boolean>>({});
  const [showAllTopics, setShowAllTopics] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setProfile(await api.profile());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setBusy(false);
      }
    })();
  }, []);

  const skillsByTopic = useMemo(() => {
    const map: Record<string, Skill[]> = {};
    for (const s of profile?.skills ?? []) (map[s.topic] ??= []).push(s);
    // Practised skills first, weakest at the top — that's what needs the work.
    for (const list of Object.values(map)) {
      list.sort((a, b) => {
        if ((a.evidence > 0) !== (b.evidence > 0)) return a.evidence > 0 ? -1 : 1;
        return a.evidence > 0 ? a.level - b.level : a.label.localeCompare(b.label);
      });
    }
    return map;
  }, [profile]);

  const weakFormulas = useMemo(
    () => (profile?.formulas ?? []).filter((f) => f.level < 55).slice(0, 8),
    [profile]
  );

  const level = profile?.level;
  const color = levelColor(level?.score ?? 0);
  const visibleTopics = (profile?.topics ?? []).filter((t) => showAllTopics || t.engaged);

  return (
    <AuthGuard>
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-baseline justify-between mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Your profile</h1>
          {profile && <span className="text-sm text-slate-500">{profile.user.email}</span>}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {busy ? (
          <p className="text-slate-500">Loading...</p>
        ) : !profile || !level ? (
          <p className="text-slate-500">Nothing yet.</p>
        ) : (
          <div className="space-y-6">
            {/* Headline skill level */}
            <div className="bg-white border border-slate-200 rounded-lg p-6">
              <div className="flex flex-wrap items-end gap-6">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-400 font-medium">
                    Skill level
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className={`text-5xl font-bold ${color.text}`}>
                      {Math.round(level.score)}
                    </span>
                    <span className="text-lg text-slate-400">/ 100</span>
                  </div>
                  <div className="text-sm font-medium text-slate-600 mt-0.5">{level.band}</div>
                </div>
                <div className="flex-1 min-w-[240px]">
                  <Bar level={level.score} className="h-3" />
                  <p className="mt-2 text-xs text-slate-500">
                    How well you do the exercise types you&apos;ve practised, weighted by how much
                    you&apos;ve proven. Getting harder exercises right raises it; wrong answers and
                    long gaps lower it.
                  </p>
                </div>
              </div>

              <div className="mt-5 grid gap-4 grid-cols-2 sm:grid-cols-4 border-t border-slate-100 pt-4">
                <div>
                  <div className="text-xl font-semibold text-slate-900">{level.attempts}</div>
                  <div className="text-xs text-slate-500">Exercises answered</div>
                </div>
                <div>
                  <div className="text-xl font-semibold text-emerald-600">{pct(level.accuracy)}</div>
                  <div className="text-xs text-slate-500">Accuracy</div>
                </div>
                <div>
                  <div className="text-xl font-semibold text-slate-900">
                    {level.topics_started}/{level.topics_total}
                  </div>
                  <div className="text-xs text-slate-500">Topics started</div>
                </div>
                <div>
                  <div className="text-xl font-semibold text-slate-900">{pct(level.coverage)}</div>
                  <div className="text-xs text-slate-500">
                    Syllabus proven ({level.practised}/{level.total} types)
                  </div>
                </div>
              </div>

              <div className="mt-5 border-t border-slate-100 pt-4">
                <div className="text-xs text-slate-500 mb-1.5">Recent activity</div>
                <ActivityStrip activity={profile.activity} />
              </div>
            </div>

            {/* What to practise next */}
            {profile.suggestions.length > 0 && (
              <div>
                <h2 className="font-semibold text-slate-900 mb-3">What to practise next</h2>
                <div className="grid gap-3 sm:grid-cols-2">
                  {profile.suggestions.map((s, i) => (
                    <SuggestionCard key={`${s.kind}-${s.skill_key ?? s.formula ?? i}`} s={s} />
                  ))}
                </div>
              </div>
            )}

            {/* Topic progress */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-slate-900">Progress by topic</h2>
                <button
                  onClick={() => setShowAllTopics((v) => !v)}
                  className="text-xs text-slate-500 hover:text-slate-900"
                >
                  {showAllTopics ? "Show started only" : "Show all topics"}
                </button>
              </div>
              <div className="space-y-2">
                {visibleTopics.map((t) => (
                  <TopicCard
                    key={t.topic}
                    topic={t}
                    skills={skillsByTopic[t.topic] ?? []}
                    open={!!openTopics[t.topic]}
                    onToggle={() => setOpenTopics((o) => ({ ...o, [t.topic]: !o[t.topic] }))}
                  />
                ))}
                {visibleTopics.length === 0 && (
                  <p className="text-sm text-slate-500">
                    No topics started yet —{" "}
                    <Link href="/practice" className="text-slate-900 underline">
                      answer a few exercises
                    </Link>{" "}
                    and this fills in.
                  </p>
                )}
              </div>
            </div>

            {weakFormulas.length > 0 && <FormulaTable formulas={weakFormulas} />}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
