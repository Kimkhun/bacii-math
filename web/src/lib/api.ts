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
  question_type: string;
  difficulty: string;
  a: number;
  b: number;
  prompt: string;
  z_display: string;
  source: string;
}

export interface DetectResult {
  raw_text: string;
  latex: string;
  tokens: string[];
  confidence: number;
}

export interface Explanation {
  content: string;
  provider: string;
  intervened: boolean;
  trigger: string;
  work_check?: { content: string; provider: string } | null;
}

export interface GradeResult {
  attempt_id: string;
  correct: boolean;
  reason: string;
  given?: string;
  expected: string;
  explanation?: Explanation;
  work_check?: { content: string; provider: string } | null;
}

export interface Attempt {
  id: string;
  question_id: string;
  user_answer: string;
  correct: boolean;
  reason: string;
  created_at: string;
}

export interface Stats {
  total_attempts: number;
  correct: number;
  accuracy: number;
  by_topic: { question_type: string; attempts: number; correct: number }[];
}

export const api = {
  signup: (email: string, password: string) =>
    request<AuthResponse>("/auth/signup", { method: "POST", body: { email, password }, auth: "none" }),
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: { email, password }, auth: "none" }),
  me: () => request<User>("/auth/me"),
  generate: (generation_mode: string, difficulty: string) =>
    request<Question>("/problems/generate", { method: "POST", body: { generation_mode, difficulty } }),
  detect: (image_base64: string) =>
    request<DetectResult>("/vision/detect", { method: "POST", body: { image_base64 } }),
  grade: (question_id: string, user_answer: string) =>
    request<GradeResult>("/problems/grade", { method: "POST", body: { question_id, user_answer } }),
  explain: (question_id: string, user_answer?: string) =>
    request<Explanation>("/problems/explain", { method: "POST", body: { question_id, user_answer } }),
  attempts: () => request<Attempt[]>("/attempts"),
  stats: () => request<Stats>("/stats"),
};
