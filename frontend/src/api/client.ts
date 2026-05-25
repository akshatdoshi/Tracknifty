import type {
  DataQuality,
  Portfolio,
  Rule,
  SignalRow,
} from "./types";

const TOKEN_KEY = "tracknifty_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const resp = await fetch(`/api${path}`, { ...init, headers });
  if (resp.status === 401) {
    clearToken();
    throw new Error("Session expired — please log in again.");
  }
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(detail || `Request failed (${resp.status})`);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export interface Me {
  id: number;
  username: string;
  role: "admin" | "manager";
}

export const api = {
  async login(username: string, password: string) {
    const body = new URLSearchParams({ username, password });
    const resp = await fetch("/api/auth/login", { method: "POST", body });
    if (!resp.ok) throw new Error("Invalid username or password");
    const data = await resp.json();
    setToken(data.access_token);
    return data as { role: string; username: string };
  },
  me: () => request<Me>("/auth/me"),
  portfolios: () => request<Portfolio[]>("/portfolios"),
  signals: (portfolioId: number) =>
    request<SignalRow[]>(`/portfolios/${portfolioId}/signals`),
  globalSignals: () => request<SignalRow[]>("/portfolios/signals/global"),
  rules: (portfolioId: number) =>
    request<Rule>(`/portfolios/${portfolioId}/rules`),
  updateRules: (portfolioId: number, patch: Partial<Rule>) =>
    request<Rule>(`/portfolios/${portfolioId}/rules`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }),
  triggerScore: () => request<{ signals_written: number }>("/webhook/score", {
    method: "POST",
  }),
  dataQuality: () => request<DataQuality>("/ingestion/quality"),
  uploadTransactions: async (portfolioId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const headers = new Headers();
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const resp = await fetch(`/api/ingestion/${portfolioId}/upload`, {
      method: "POST",
      headers,
      body: form,
    });
    if (!resp.ok) throw new Error(await resp.text());
    return resp.json();
  },
};
