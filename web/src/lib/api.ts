const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8016";

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
  step_check?: StepCheck | null;
  steps?: { step_order: number; title: string; detail: string; formula?: string | null }[];
}

export interface PartVerdict {
  label: string;
  correct: boolean;
  reason?: string;
  given?: string | null;
  expected?: string;
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
  step_check?: StepCheck | null;
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
  created_at: string;
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

export interface FormulaEntry {
  id: string;
  name_en: string | null;
  name_km: string;
  latex: string | null;
  weight: number;
  formulas: string[];
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
}

export interface TemplateStructures {
  topics: { topic: string; question_types: { question_type: string; structures: TemplateStructure[] }[] }[];
}

export interface Stats {
  total_attempts: number;
  correct: number;
  accuracy: number;
  by_topic: { question_type: string; attempts: number; correct: number }[];
  by_formula?: FormulaStat[];
}

export const api = {
  signup: (email: string, password: string) =>
    request<AuthResponse>("/auth/signup", { method: "POST", body: { email, password }, auth: "none" }),
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: { email, password }, auth: "none" }),
  me: () => request<User>("/auth/me"),
  generate: (generation_mode: string, difficulty: string, topic: string = "complex", question_type?: string) =>
    request<Question>("/problems/generate", {
      method: "POST",
      body: { generation_mode, difficulty, topic, question_type },
    }),
  replay: (question_id: string) =>
    request<Question>("/problems/replay", { method: "POST", body: { question_id } }),
  detect: (image_base64: string) =>
    request<DetectResult>("/vision/detect", { method: "POST", body: { image_base64 } }),
  grade: (question_id: string, user_answer: string, work_text?: string, lines_boxes?: (number[] | null)[], part?: string) =>
    request<GradeResult>("/problems/grade", {
      method: "POST",
      body: { question_id, user_answer, work_text, lines_boxes, part },
    }),
  explain: (question_id: string, user_answer?: string, work_text?: string) =>
    request<Explanation>("/problems/explain", { method: "POST", body: { question_id, user_answer, work_text } }),
  attempts: () => request<Attempt[]>("/attempts"),
  attempt: (id: string) => request<AttemptDetail>(`/attempts/${id}`),
  stats: () => request<Stats>("/stats"),
  formulas: () => request<FormulaCatalog>("/formulas"),
  templates: () => request<TemplateInventory>("/templates"),
  templateStructures: () => request<TemplateStructures>("/templates/structures"),
};
