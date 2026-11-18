// Thin client for the Python agent API (agent-api/). All logic lives there; this only fetches.
import type { Approval, FollowUp, Meeting, Request } from "@/lib/mock-data";

export type Settings = {
  workingHours: { start: string; end: string };
  sensitiveKeywords: string[];
  replyTemplates: string[];
  timezone: string;
  briefTime: string;
  pollMinutes: number;
};

export type State = {
  requests: Request[];
  meetings: Meeting[];
  approvals: Approval[];
  followUps: FollowUp[];
  settings: Settings;
  brief: { text: string; generatedAt: string } | null;
  google: { connected: boolean; email: string | null };
};

export const BASE = process.env.AGENT_API_URL ?? "http://localhost:8000";

// Returns the error message instead of throwing so pages and buttons can show it.
export async function callApi<T>(path: string, method = "GET", body?: unknown): Promise<{ data?: T; error?: string }> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      method,
      cache: "no-store",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const j = await res.json().catch(() => null);
      return { error: j?.detail ?? `Agent API returned ${res.status}` };
    }
    return { data: (await res.json()) as T };
  } catch {
    return { error: `Cannot reach the agent API at ${BASE}. Start it: cd agent-api && uv run uvicorn app.main:app --port 8000` };
  }
}

export const getState = () => callApi<State>("/state");
