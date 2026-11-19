// Thin client for the Python agent API (agent-api/). All logic lives there; this only fetches.
// Server-only: it sends the shared API key, which must never reach the browser.
import { connection } from "next/server";
import type { Approval, AuditEntry, FollowUp, Kpis, Meeting, Request } from "@/lib/types";

export type Settings = {
  workingHours: { start: string; end: string };
  sensitiveKeywords: string[];
  replyTemplates: string[];
  timezone: string;
  briefTime: string;
  pollMinutes: number;
  attendeeAllowDomains: string[];
  reminderMinutes: number;
  escalationAlerts: boolean;
  workingDays: number[]; // 0 = Monday ... 6 = Sunday
  minNoticeMinutes: number;
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

// FastAPI validation errors come back as a list of {loc, msg}; turn them into one readable line.
function detailText(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(" › ")}: ${d.msg ?? "invalid"}`)
      .join("; ");
  }
  return `Agent API returned ${status}`;
}

// Returns the error message instead of throwing so pages and buttons can show it.
export async function callApi<T>(path: string, method = "GET", body?: unknown): Promise<{ data?: T; error?: string }> {
  const key = process.env.AGENT_API_KEY;
  if (!key) return { error: "AGENT_API_KEY is not set on the Next server. Add it to project/.env.local (same value as agent-api/.env)." };
  try {
    const res = await fetch(`${BASE}${path}`, {
      method,
      cache: "no-store",
      headers: { "X-API-Key": key, ...(body ? { "Content-Type": "application/json" } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const j = await res.json().catch(() => null);
      return { error: detailText(j?.detail, res.status) };
    }
    return { data: (await res.json()) as T };
  } catch {
    return { error: `Cannot reach the agent API at ${BASE}. Start it: cd agent-api && uv run uvicorn app.main:app --port 8000` };
  }
}

// Pages call these. connection() keeps them out of build-time prerendering: without it a build with no API key or
// no API running would bake the error message into static HTML.
export const getState = async () => {
  await connection();
  return callApi<State>("/state");
};
export const getKpis = async () => {
  await connection();
  return callApi<Kpis>("/kpis?days=30");
};
export const getAudit = async (event?: string) => {
  await connection();
  return callApi<{ entries: AuditEntry[]; events: string[] }>(`/audit?limit=200${event ? `&event=${encodeURIComponent(event)}` : ""}`);
};
