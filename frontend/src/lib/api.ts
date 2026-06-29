export interface ContentJob {
  id: string;
  topic: string;
  content_type: string;
  tone: string;
  target_audience: string | null;
  status: string;
  research_notes: string | null;
  draft_content: string | null;
  final_content: string | null;
  agent_logs: Array<{ agent: string; action: string; summary: string }> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateJobRequest {
  topic: string;
  content_type?: string;
  tone?: string;
  target_audience?: string;
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? "/api/v1" : "http://localhost:8000/api/v1");

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function createJob(data: CreateJobRequest): Promise<ContentJob> {
  const response = await fetch(`${API_URL}/content`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<ContentJob>(response);
}

export async function listJobs(): Promise<ContentJob[]> {
  const response = await fetch(`${API_URL}/content`, { cache: "no-store" });
  return handleResponse<ContentJob[]>(response);
}

export async function getJob(id: string): Promise<ContentJob> {
  const response = await fetch(`${API_URL}/content/${id}`, { cache: "no-store" });
  return handleResponse<ContentJob>(response);
}

export async function deleteJob(id: string): Promise<void> {
  const response = await fetch(`${API_URL}/content/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}`);
  }
}
