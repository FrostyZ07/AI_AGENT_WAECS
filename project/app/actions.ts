"use server";

import { revalidatePath } from "next/cache";
import { callApi, type Settings } from "@/lib/api";
import { authError } from "@/lib/auth";

// Each action returns an error message (or null on success) so the buttons can display it.
async function run(path: string, method: string, body?: unknown): Promise<string | null> {
  const denied = await authError();
  if (denied) return denied;
  const { error } = await callApi(path, method, body);
  revalidatePath("/", "layout");
  return error ?? null;
}

export async function processInboxAction() {
  return run("/process-inbox", "POST");
}

export async function generateBriefAction() {
  return run("/brief", "POST");
}

// `edits` are what the principal changed on the card: the edited reply, the invite list, or the reason for rejecting.
export async function decideApprovalAction(
  id: string,
  status: "approved" | "rejected",
  edits?: { draft?: string; attendees?: string[]; note?: string; start?: string; end?: string },
) {
  return run(`/approvals/${encodeURIComponent(id)}`, "POST", { status, ...edits });
}

export async function saveSettingsAction(settings: Settings) {
  return run("/settings", "PUT", settings);
}

export async function disconnectGoogleAction() {
  return run("/oauth/google/disconnect", "POST");
}

export async function prepMeetingAction(eventId: string) {
  return run(`/meetings/${encodeURIComponent(eventId)}/prep`, "POST");
}

export async function completeFollowUpAction(id: string) {
  return run(`/follow-ups/${encodeURIComponent(id)}/done`, "POST");
}
