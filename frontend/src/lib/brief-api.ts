const API_URL = (() => {
  const env = process.env.NEXT_PUBLIC_API_URL;
  if (env) return env.replace("/api/v1", "");
  if (typeof window !== "undefined") return "";
  return "http://localhost:8000";
})();

export interface ContentBrief {
  topic: string;
  keywords: string[];
  target_audience: string;
  brand_voice: string;
  content_type: string;
  target_length: number;
}

export interface BriefCreateResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface BriefStatus {
  task_id: string;
  status: string;
  current_node: string | null;
  error_message: string | null;
  updated_at: string;
}

let cachedToken: string | null = null;

async function getToken(): Promise<string> {
  if (cachedToken) return cachedToken;
  const clientId = typeof window !== "undefined"
    ? localStorage.getItem("client_id") || "default"
    : "default";
  if (typeof window !== "undefined") {
    localStorage.setItem("client_id", clientId);
  }
  const res = await fetch(`${API_URL}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId }),
  });
  if (!res.ok) throw new Error("Failed to get auth token");
  const data = await res.json();
  cachedToken = data.access_token;
  return cachedToken!;
}

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = await getToken();
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Content-Type", "application/json");
  return fetch(`${API_URL}${path}`, { ...options, headers });
}

export async function createBrief(brief: ContentBrief): Promise<BriefCreateResponse> {
  const res = await authFetch("/briefs", {
    method: "POST",
    body: JSON.stringify(brief),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getBriefStatus(taskId: string): Promise<BriefStatus> {
  const res = await authFetch(`/briefs/${taskId}/status`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getContent(contentId: string) {
  const res = await authFetch(`/content/${contentId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function approveContent(
  contentId: string,
  approved: boolean,
  feedback?: string,
) {
  const res = await authFetch(`/content/${contentId}/approve`, {
    method: "POST",
    body: JSON.stringify({ approved, feedback }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function getWsUrl(taskId: string): string {
  if (!API_URL && typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}/ws/${taskId}`;
  }
  const base = API_URL.replace("http://", "ws://").replace("https://", "wss://");
  return `${base}/ws/${taskId}`;
}
