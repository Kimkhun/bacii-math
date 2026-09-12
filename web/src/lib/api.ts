const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8016";

import type { StrokeDocument } from "@/components/Canvas";

export type StrokeDoc = StrokeDocument;

const ACCESS_KEY = "bacii_access";
const REFRESH_KEY = "bacii_refresh";

export function getAccess(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefresh(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: "refresh" | "none";
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = "refresh" } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const access = getAccess();
  if (access) headers["Authorization"] = `Bearer ${access}`;

  let res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && auth === "refresh" && getRefresh()) {
    const ok = await refreshToken();
    if (ok) {
      const newAccess = getAccess();
      if (newAccess) headers["Authorization"] = `Bearer ${newAccess}`;
      res = await fetch(`${API_URL}${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } else {
      clearTokens();
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new Error("Session expired");
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : res.statusText);
  }

  return res.json() as Promise<T>;
}

export async function refreshToken(): Promise<boolean> {
  const rt = getRefresh();
  if (!rt) return false;
  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: rt }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export interface User {
  id: string;
  email: string;
  plan: string;
  is_admin: boolean;
  created_at: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
}

export interface Question {
  id: string;
  topic: string;
  question_type: string;
  difficulty: string;
  a?: number | null;
  b?: number | null;
  params: Record<string, any>;
  prompt: string;
  prompt_latex: string | null;
  z_display: string;
  source: string;
  formula_tags?: string[];
  formula_difficulty?: string;
}

export interface QuestionStep {
  step_order: number;
  title: string;
  detail: string;
  formula?: string | null;
}

export interface QuestionDetail {
  id: string;
  question_type: string;
  difficulty: string;
  prompt: string;
  prompt_latex: string | null;
  z_display: string;
  source: string;
  formula_tags: string[];
  formula_difficulty?: string | null;
  steps: QuestionStep[];
  graph?: GraphSpec | null;
}

export interface DetectResult {
  lines: string[];
  lines_latex: string[];
  raw_text: string;
  latex: string;
  tokens: string[];
  confidence: number;
  provider?: string;
  lines_boxes?: (number[] | null)[];
  lines_confidence?: number[];
  lines_alt?: string[][];
  lines_alt_latex?: string[][];
}

export interface StepCheckLine {
  line: number;
  text: string;
  checked: boolean;
  correct?: boolean;
  matches?: string;
  formula?: string | null;
  reason?: string;
}

export interface FormulaResult {
  formula: string;
  label: string;
  reached: boolean;
  line: number | null;
}

export interface StepCheck {
  line_results: StepCheckLine[];
  first_error_line: number | null;
  reached_final_answer: boolean;
  formula_breakdown?: FormulaResult[];
}

export interface Explanation {
  content: string;
  provider: string;
  intervened: boolean;
  trigger: string;
  work_check?: { content: string; provider: string } | null;
  teacher_feedback?: { content: string; provider: string } | null;
  step_check?: StepCheck | null;
  steps?: { step_order: number; title: string; detail: string; formula?: string | null }[];
  graph?: GraphSpec | null;
  graph_check?: GraphCheck | null;
}

export interface PartVerdict {
  label: string;
  correct: boolean;
  reason?: string;
  given?: string | null;
  expected?: string;
  note?: string;
}

export interface GraphPoint {
  x: number;
  y: number;
  label?: string;
}

export interface GraphSpec {
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
  curve: number[][][];
  vertical_asymptotes: number[];
  tangent?: number[][];
  tangents?: number[][][];
  asymptote_lines?: {
    kind: string;
    points: number[][];
    line: string;
    label?: string;
  }[];
  points: GraphPoint[];
}

export interface GraphCheckItem {
  label: string;
  found: boolean;
}

export interface GraphCheck {
  items: GraphCheckItem[];
  found: number;
  total: number;
}

export interface GraphGradeResult {
  score?: number;
  curve_correct?: boolean;
  asymptotes_correct?: boolean;
  tangent_correct?: boolean | null;
  points_correct?: boolean;
  feedback?: string;
  suggestions?: string[];
  error?: string;
  message?: string;
}

export interface RubricScore {
  earned: number;
  possible: number;
  breakdown: {
    item: string;
    label: string;
    points_earned: number;
    points_possible: number;
    matched_line: string | null;
  }[];
}

export interface GradeResult {
  attempt_id: string;
  correct: boolean;
  reason: string;
  given?: string;
  expected: string;
  parts?: PartVerdict[];
  part?: string;
  all_complete?: boolean;
  explanation?: Explanation;
  work_check?: { content: string; provider: string } | null;
  teacher_feedback?: { content: string; provider: string } | null;
  step_check?: StepCheck | null;
  graph?: GraphSpec | null;
  graph_check?: GraphCheck | null;
  rubric_score?: RubricScore | null;
}

export interface Attempt {
  id: string;
  question_id: string;
  topic: string;
  question_type: string;
  difficulty: string;
  prompt: string;
  prompt_latex: string | null;
  expected_answer: string;
  user_answer: string;
  correct: boolean;
  reason: string;
  formula_breakdown?: FormulaResult[] | null;
  work_text?: string | null;
  step_check?: StepCheck | null;
  hints_used?: number;
  strokes_thumb?: string | null;
  created_at: string;
}

export interface SavedPartState {
  typed?: string;
  work_text?: string | null;
  lines_boxes?: (number[] | null)[] | null;
  strokes?: StrokeDoc | null;
  strokes_thumb?: string | null;
  correct?: boolean;
}

export interface SessionSummary {
  id: string;
  question_id: string;
  status: string;
  parts_done: number;
  parts_total: number;
  updated_at: string;
  question?: {
    id: string;
    topic: string;
    question_type: string;
    difficulty: string;
    prompt: string;
    prompt_latex: string | null;
  };
}

export interface SessionDetail {
  id: string;
  status: string;
  updated_at: string;
  question: Question;
  parts: Record<string, SavedPartState>;
}

export interface AttemptDetail {
  id: string;
  user_answer: string;
  parsed_answer?: string | null;
  correct: boolean;
  reason: string;
  work_text?: string | null;
  step_check?: StepCheck | null;
  lines_boxes?: (number[] | null)[] | null;
  formula_breakdown?: FormulaResult[] | null;
  hints_used?: number;
  strokes?: StrokeDoc | null;
  strokes_thumb?: string | null;
  created_at: string;
  question: {
    id: string;
    topic: string;
    question_type: string;
    difficulty: string;
    prompt: string;
    prompt_latex: string | null;
    expected_answer: string;
    formula_tags: string[];
    steps: { step_order: number; title: string; detail: string; formula?: string | null }[];
  } | null;
  explanations: { provider: string; content: string; trigger: string; created_at: string }[];
}

export interface FormulaStat {
  formula: string;
  name_en?: string;
  attempts: number;
  reached: number;
  missed: number;
}

export interface FormulaVariant {
  topic: string;
  question_type: string;
  variant: string | null;
  difficulty: string;
}

export interface FormulaEntry {
  id: string;
  name_en: string | null;
  name_km: string;
  latex: string | null;
  weight: number;
  formulas: string[];
  variants: FormulaVariant[];
}

export interface FormulaCatalog {
  topics: { topic: string; entries: FormulaEntry[] }[];
}

export interface TemplateSample {
  difficulty: string;
  variant?: string | null;
  params: Record<string, string>;
  prompt: string;
  prompt_latex: string | null;
  answer: string;
  answer_latex?: string | null;
  formula_tags: string[];
}

export interface TemplateInventory {
  topics: { topic: string; question_types: { question_type: string; difficulties: TemplateSample[] }[] }[];
}

export interface TemplateStructure {
  id: string;
  question_type: string;
  difficulty: string;
  pattern: string;
  pattern_latex: string | null;
  sample_prompt: string;
  sample_prompt_latex: string | null;
  sample_answer: string;
  sample_answer_latex?: string | null;
  formula_tags: string[];
  source_labels: string[];
  graph?: GraphSpec | null;
  solution_km?: string | null;
  parts?: {
    label: string;
    want?: string;
    answer_kind?: string;
    question_km?: string;
    technique?: string;
    answer: string;
    answer_latex?: string;
    answer_display?: string;
  }[];
}

export interface TemplateStructures {
  topics: { topic: string; question_types: { question_type: string; structures: TemplateStructure[] }[] }[];
}

export interface TemplateSummary {
  topics: {
    topic: string;
    question_types: { question_type: string; count: number }[];
    structure_count: number;
    difficulties: string[];
    curated: number;
  }[];
}

// --- admin sandbox ----------------------------------------------------------

export interface SandboxSample {
  params: Record<string, unknown>;
  prompt: string | null;
  prompt_latex: string | null;
}

export interface SandboxCheckpoint {
  label: string;
  value: string;
  formula: string | null;
}

export interface SandboxSolveResult {
  answer_exact: string;
  answer_decimal: number | string | null;
  answer_latex: string;
  steps: { title: string; detail: string; formula: string | null }[];
  formula_tags: string[];
  checkpoints: SandboxCheckpoint[];
  parts?: { label: string; answer_exact: string; answer_latex: string; answer_kind: string | null }[];
  params_used: Record<string, unknown>;
}

export interface SandboxLineResult {
  line: number;
  text: string;
  checked: boolean;
  correct?: boolean;
  matches?: string;
  formula?: string | null;
  expected?: string;
  reason?: string;
}

export interface SandboxRubricStep {
  item: string;
  label: string;
  points_earned: number;
  points_possible: number;
  matched_line: string | null;
  implied?: boolean;
}

export interface SandboxGradeResult {
  step_check: {
    line_results: SandboxLineResult[];
    first_error_line: number | null;
    formula_breakdown: { label: string; formula: string | null; reached: boolean }[];
  };
  rubric_score?: { earned: number; possible: number; breakdown: SandboxRubricStep[] };
  rubric_error?: string;
  graph_check?: unknown;
  graph_check_error?: string;
}

export interface Stats {
  total_attempts: number;
  correct: number;
  accuracy: number;
  by_topic: { question_type: string; attempts: number; correct: number }[];
  by_formula?: FormulaStat[];
}

// --- profile / skill progress ---------------------------------------------
// The backend tracks one "skill" per practisable exercise type (a technique
// like sin(x)/x limits, not a whole topic) plus one per formula the
// step-checker watches. See backend/engine/core/mastery.py for what the
// numbers mean.

export interface SkillEstimate {
  /** Recency-weighted success rate over recent attempts, 0-1. */
  rate: number;
  /** How much proof there is, in (time-decayed) attempts. 0 = never tried. */
  evidence: number;
  /** Ability estimate, shrunk toward a pessimistic prior when evidence is thin. */
  ability: number;
  /** How certain that ability estimate is, 0-1. */
  confidence: number;
  /** The 0-100 bar: 100 * ability * confidence. */
  level: number;
}

export interface Skill extends SkillEstimate {
  key: string;
  topic: string;
  topic_label: string;
  question_type: string;
  variant: string | null;
  label: string;
  difficulty: string;
  practice: boolean;
  forceable: boolean;
  attempts: number;
  correct: number;
  streak: number;
  best_streak: number;
  days_idle: number;
  last_seen_at: string | null;
  status: "untouched" | "learning" | "shaky" | "solid" | "mastered";
  band: string;
  weak_formulas: { formula: string; name: string; level: number }[];
}

export interface FormulaSkill extends SkillEstimate {
  formula: string;
  name: string;
  latex: string | null;
  topic: string | null;
  topic_label: string | null;
  attempts: number;
  correct: number;
  days_idle: number;
  status: string;
  /** Which exercise type to practise to drill this formula, if any. */
  skill_key: string | null;
}

export interface Aggregate {
  /** 0-100 over the skills actually practised — the headline bar. */
  score: number;
  /** The same total spread over every skill, so untouched material counts 0. */
  syllabus_score: number;
  mastery: number;
  coverage: number;
  practised: number;
  total: number;
  band: string;
}

export interface TopicProgress extends Aggregate {
  topic: string;
  label: string;
  practice: boolean;
  engaged: boolean;
  skills_total: number;
  skills_practised: number;
  attempts: number;
  correct: number;
  strongest: string | null;
  weakest: string | null;
}

export type SuggestionKind =
  | "weak_skill"
  | "weak_formula"
  | "rusty_skill"
  | "unproven_skill"
  | "new_skill"
  | "new_topic"
  | "first_steps";

export interface Suggestion {
  kind: SuggestionKind;
  priority: number;
  title: string;
  reason: string;
  contrast: string | null;
  detail: string | null;
  topic: string | null;
  topic_label: string | null;
  skill_key: string | null;
  formula: string | null;
  level: number;
  target: { topic: string; question_type: string; variant: string | null; difficulty: string } | null;
}

export interface Profile {
  user: { id: string; email: string; plan: string; member_since: string | null };
  level: Aggregate & {
    attempts: number;
    correct: number;
    accuracy: number;
    topics_started: number;
    topics_total: number;
  };
  topics: TopicProgress[];
  skills: Skill[];
  formulas: FormulaSkill[];
  suggestions: Suggestion[];
  activity: { date: string; attempts: number; correct: number }[];
}

export interface ExamQuestion {
  label: string;
  prompt_en?: string;
  prompt_latex?: string;
  answer_latex?: string;
  gradable: boolean;
}

export interface ExamSection {
  id: string;
  title_en?: string;
  title_km?: string;
  given_en?: string;
  given_km?: string;
  given_latex?: string;
  questions: ExamQuestion[];
}

export interface Exam {
  exam_id: string;
  exam_date?: string;
  duration_minutes?: number;
  total_points?: number;
  sections: ExamSection[];
}

export interface ExamQuestionResult {
  earned: number;
  possible: number;
  breakdown: {
    item: string;
    label: string;
    points_earned: number;
    points_possible: number;
    matched_line: string | null;
  }[];
}

export interface ExamResult {
  earned: number;
  possible: number;
  per_question: Record<string, ExamQuestionResult>;
}

export const api = {
  signup: (email: string, password: string) =>
    request<AuthResponse>("/auth/signup", { method: "POST", body: { email, password }, auth: "none" }),
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: { email, password }, auth: "none" }),
  me: () => request<User>("/auth/me"),
  generate: (generation_mode: string, difficulty: string, topic: string = "complex", question_type?: string, variant?: string) =>
    request<Question>("/problems/generate", {
      method: "POST",
      body: { generation_mode, difficulty, topic, question_type, variant },
    }),
  replay: (question_id: string) =>
    request<Question>("/problems/replay", { method: "POST", body: { question_id } }),
  question: (question_id: string) => request<QuestionDetail>(`/problems/${question_id}`),
  detect: (image_base64: string) =>
    request<DetectResult>("/vision/detect", { method: "POST", body: { image_base64 } }),
  grade: (
    question_id: string,
    user_answer: string,
    work_text?: string,
    lines_boxes?: (number[] | null)[],
    part?: string,
    hints_used?: number,
    strokes?: StrokeDoc | null,
    strokes_thumb?: string | null,
    lang?: string
  ) =>
    request<GradeResult>("/problems/grade", {
      method: "POST",
      body: { question_id, user_answer, work_text, lines_boxes, part, hints_used, strokes, strokes_thumb, lang },
    }),
  explain: (question_id: string, user_answer?: string, work_text?: string, lang?: string) =>
    request<Explanation>("/problems/explain", { method: "POST", body: { question_id, user_answer, work_text, lang } }),
  saveProgress: (
    question_id: string,
    part?: string,
    typed?: string,
    work_text?: string,
    lines_boxes?: (number[] | null)[],
    strokes?: StrokeDoc | null,
    strokes_thumb?: string | null
  ) =>
    request<SessionSummary>("/problems/progress/save", {
      method: "POST",
      body: { question_id, part, typed, work_text, lines_boxes, strokes, strokes_thumb },
    }),
  myProgress: () => request<SessionSummary[]>("/progress"),
  progress: (id: string) => request<SessionDetail>(`/progress/${id}`),
  deleteProgress: (id: string) => request<{ deleted: boolean }>(`/progress/${id}`, { method: "DELETE" }),
  attempts: () => request<Attempt[]>("/attempts"),
  attempt: (id: string) => request<AttemptDetail>(`/attempts/${id}`),
  stats: () => request<Stats>("/stats"),
  profile: () => request<Profile>("/profile"),
  rebuildProfile: () =>
    request<{ rebuilt: boolean; attempts_replayed: number }>("/profile/rebuild", { method: "POST" }),
  skillCatalog: () =>
    request<{ topics: string[]; labels: Record<string, string>; skills: Skill[] }>("/skills"),
  formulas: () => request<FormulaCatalog>("/formulas"),
  templates: () => request<TemplateInventory>("/templates"),
  templateStructures: (topic?: string) =>
    request<TemplateStructures>(`/templates/structures${topic ? `?topic=${topic}` : ""}`),
  templateSummary: () => request<TemplateSummary>("/templates/summary"),
  sandboxSample: (topic: string, question_type: string, difficulty = "medium") =>
    request<SandboxSample>(
      `/sandbox/sample?topic=${encodeURIComponent(topic)}&question_type=${encodeURIComponent(question_type)}&difficulty=${difficulty}`
    ),
  sandboxStructureSample: (topic: string, question_type: string, structure_id: string) =>
    request<SandboxSample>(
      `/sandbox/structure-sample?topic=${encodeURIComponent(topic)}&question_type=${encodeURIComponent(question_type)}&structure_id=${encodeURIComponent(structure_id)}`
    ),
  sandboxSolve: (topic: string, question_type: string, params: Record<string, unknown>) =>
    request<SandboxSolveResult>("/sandbox/solve", { method: "POST", body: { topic, question_type, params } }),
  sandboxGrade: (topic: string, question_type: string, params: Record<string, unknown>, lines: string) =>
    request<SandboxGradeResult>("/sandbox/grade", { method: "POST", body: { topic, question_type, params, lines } }),
  gradeGraph: (question_id: string, strokes_thumb: string) =>
    request<GraphGradeResult>("/problems/grade-graph", {
      method: "POST",
      body: { question_id, strokes_thumb },
    }),
  exam: (exam_id: string) => request<Exam>(`/problems/exam/${exam_id}`),
  submitExam: (exam_id: string, answers: Record<string, string>) =>
    request<ExamResult>(`/problems/exam/${exam_id}/submit`, {
      method: "POST",
      body: { answers },
    }),
  regenerateStructure: (structure_id: string) =>
    request<{ structure: TemplateStructure }>("/templates/structures/regenerate", {
      method: "POST",
      body: { structure_id },
    }),
  adminModelSettings: () => request<{ text_model: string; vision_model: string; vision_provider: string }>("/admin/model-settings"),
  updateAdminModelSettings: (settings: { text_model: string; vision_model: string; vision_provider: string }) =>
    request<{ status: string; settings: any }>("/admin/model-settings", {
      method: "POST",
      body: settings,
    }),
  adminCostSummary: (days: number = 30) => request<AdminCostSummary>(`/admin/costs/summary?days=${days}`),
  adminUserCosts: (days: number = 30, endpoint?: string) =>
    request<AdminUserCost[]>(`/admin/costs/users?days=${days}${endpoint ? `&endpoint=${endpoint}` : ""}`),
  adminUsageLogs: (limit: number = 50, endpoint?: string) =>
    request<AdminUsageLog[]>(`/admin/costs/logs?limit=${limit}${endpoint ? `&endpoint=${endpoint}` : ""}`),
};

export interface AdminCostSummary {
  timeframe_days: number;
  today: {
    calls: number;
    total_tokens: number;
    cost_usd: number;
  };
  period: {
    calls: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    cost_usd: number;
    avg_latency_ms: number;
  };
  by_endpoint: Array<{
    endpoint: string;
    calls: number;
    total_tokens: number;
    cost_usd: number;
  }>;
  by_model: Array<{
    model_name: string;
    calls: number;
    total_tokens: number;
    cost_usd: number;
  }>;
}

export interface AdminUserCost {
  user_id: string;
  email: string;
  total_calls: number;
  total_tokens: number;
  total_cost_usd: number;
  last_active: string | null;
}

export interface AdminUsageLog {
  id: string;
  user_id: string | null;
  email: string;
  endpoint: string;
  provider: string;
  model_name: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  latency_ms: number;
  success: boolean;
  error_message: string | null;
  created_at: string;
}
