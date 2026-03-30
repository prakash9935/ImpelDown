import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: { error?: string; reason?: string; detail?: string }
  ) {
    super(body.error || body.detail || `API error ${status}`);
  }
}

async function getAuthHeaders(): Promise<HeadersInit> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) return {};
  return { Authorization: `Bearer ${session.access_token}` };
}

async function handleResponse(res: Response) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));

    if (res.status === 401) {
      const supabase = createClient();
      await supabase.auth.signOut();
      window.location.href = "/login";
    }

    throw new ApiError(res.status, body);
  }
  return res.json();
}

export async function apiGet<T>(path: string): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}${path}`, { headers });
  return handleResponse(res);
}

export async function apiPost<T>(
  path: string,
  body: Record<string, unknown>
): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse(res);
}

export async function apiUpload<T>(
  path: string,
  formData: FormData
): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers, // No Content-Type — browser sets multipart boundary
    body: formData,
  });
  return handleResponse(res);
}

// Response types
export interface HealthResponse {
  status: "ok" | "degraded";
  qdrant: "ok" | "down";
  redis: "ok" | "degraded";
}

export interface QueryResponse {
  response: string;
  chunks_used: string[];
  latency_ms: number;
  tokens_used: number;
  is_safe: boolean;
  pii_redacted: boolean;
  cache_hit?: boolean;
}

export interface IngestResponse {
  status: "success" | "partial" | "error";
  file_name: string;
  chunks_ingested: number;
  chunks_quarantined: number;
  errors: string[];
}
